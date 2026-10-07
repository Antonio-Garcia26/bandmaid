import "server-only";

import { Redis } from "@upstash/redis";
import { Ratelimit } from "@upstash/ratelimit";
import type { NextRequest } from "next/server";
import { configuredValue } from "@/lib/security/config";
import { jsonError, pendingResponse } from "@/lib/security/responses";
import { trustedClientIp } from "@/lib/security/ip";

type Entry = { count: number; resetAt: number };
type RateLimitResult = { allowed: boolean; retryAfter: number };
type ProductionCheck = { result: RateLimitResult } | { pending: true } | { unavailable: true };
type RateLimitWindow = { values: Map<string, Entry> };
type RateLimitGlobal = typeof globalThis & { __bandmaidRateLimitWindow?: RateLimitWindow };

const globalState = globalThis as RateLimitGlobal;
const localWindow = (globalState.__bandmaidRateLimitWindow ??= { values: new Map() });
const upstashLimiters = new Map<string, Ratelimit>();

function localLimit(key: string): RateLimitResult {
  const now = Date.now();
  for (const [candidate, entry] of localWindow.values) {
    if (entry.resetAt <= now) localWindow.values.delete(candidate);
  }
  if (localWindow.values.size > 10_000) {
    for (const candidate of localWindow.values.keys()) {
      localWindow.values.delete(candidate);
      if (localWindow.values.size <= 8_000) break;
    }
  }

  const current = localWindow.values.get(key);
  if (!current || current.resetAt <= now) {
    localWindow.values.set(key, { count: 1, resetAt: now + 60_000 });
    return { allowed: true, retryAfter: 0 };
  }
  if (current.count >= 5) return { allowed: false, retryAfter: Math.max(1, Math.ceil((current.resetAt - now) / 1000)) };
  current.count += 1;
  return { allowed: true, retryAfter: 0 };
}

function getUpstashLimiter(scope: string): Ratelimit | null {
  const url = configuredValue("UPSTASH_REDIS_REST_URL");
  const token = configuredValue("UPSTASH_REDIS_REST_TOKEN");
  if (!url || !token) return null;
  const existing = upstashLimiters.get(scope);
  if (existing) return existing;

  try {
    const redis = new Redis({ url, token });
    const limiter = new Ratelimit({
      redis,
      limiter: Ratelimit.slidingWindow(5, "60 s"),
      prefix: `bandmaid:ratelimit:${scope}`,
      analytics: false,
    });
    upstashLimiters.set(scope, limiter);
    return limiter;
  } catch {
    return null;
  }
}

async function checkLimit(scope: string, subject: string): Promise<RateLimitResult | ProductionCheck> {
  const key = `${scope}:${subject}`;
  if (process.env.NODE_ENV !== "production") return localLimit(key);

  if (!configuredValue("UPSTASH_REDIS_REST_URL") || !configuredValue("UPSTASH_REDIS_REST_TOKEN")) {
    return { pending: true };
  }

  const limiter = getUpstashLimiter(scope);
  if (!limiter) return { unavailable: true };
  try {
    const result = await limiter.limit(subject);
    if (result.reason === "timeout") return { unavailable: true };
    return { result: {
        allowed: result.success,
        retryAfter: Math.max(1, Math.ceil((result.reset - Date.now()) / 1000)),
      },
    };
  } catch {
    return { unavailable: true };
  }
}

export async function enforceRateLimit(
  request: NextRequest,
  scope: string,
  uid?: string,
  options: { includeIp?: boolean } = {},
): Promise<Response | null> {
  if (options.includeIp !== false) {
    const ip = trustedClientIp(request);
    const ipResult = await checkLimit(`${scope}:ip`, ip);
    if ("pending" in ipResult) return pendingResponse("Upstash Redis para limitar solicitudes");
    if ("unavailable" in ipResult) return jsonError("El control de solicitudes no está disponible.", 503, "RATE_LIMIT_UNAVAILABLE");
    const ipLimit = "result" in ipResult ? ipResult.result : ipResult;
    if (!ipLimit.allowed) {
      return jsonError("Demasiadas solicitudes. Inténtalo de nuevo en un minuto.", 429, "RATE_LIMITED", {
        "Retry-After": String(ipLimit.retryAfter),
      });
    }
  }

  if (uid) {
    const userResult = await checkLimit(`${scope}:uid`, uid);
    if ("pending" in userResult) return pendingResponse("Upstash Redis para limitar solicitudes");
    if ("unavailable" in userResult) return jsonError("El control de solicitudes no está disponible.", 503, "RATE_LIMIT_UNAVAILABLE");
    const userLimit = "result" in userResult ? userResult.result : userResult;
    if (!userLimit.allowed) {
      return jsonError("Demasiadas solicitudes. Inténtalo de nuevo en un minuto.", 429, "RATE_LIMITED", {
        "Retry-After": String(userLimit.retryAfter),
      });
    }
  }

  return null;
}
