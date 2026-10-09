import type { NextRequest } from "next/server";
import { connection } from "next/server";
import { getFirebaseAdmin } from "@/lib/firebase-admin";
import { getSessionUser } from "@/lib/security/auth";
import { validateApiRequest } from "@/lib/security/request-guard";

export async function GET(request: NextRequest) {
  await connection();
  const apiGuard = validateApiRequest(request);
  if (apiGuard) return apiGuard;
  const services = getFirebaseAdmin();
  const user = services ? await getSessionUser(request) : null;
  const configured = Boolean(services) || process.env.NODE_ENV !== "production";
  return Response.json(
    { user, configured, isDevMode: !services && process.env.NODE_ENV !== "production" },
    { headers: { "Cache-Control": "no-store" } },
  );
}
