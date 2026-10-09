import "server-only";

import { createHmac, randomBytes, randomInt } from "node:crypto";
import { configuredValue } from "@/lib/security/config";
import { constantTimeMatch } from "@/lib/security/constant-time";

const CAPTCHA_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";
const CAPTCHA_LENGTH = 5;
const CAPTCHA_TTL_MS = 5 * 60 * 1000; // 5 minutos de validez

type CaptchaPayload = {
  id: string;
  iat: number;
  exp: number;
  hash: string;
};

type CaptchaGlobal = typeof globalThis & {
  __bandmaidConsumedCaptchas?: Map<string, number>;
  __bandmaidCaptchaSecret?: string;
};

const globalState = globalThis as CaptchaGlobal;
const consumedCaptchas = (globalState.__bandmaidConsumedCaptchas ??= new Map<string, number>());

function getCaptchaSecret(): string {
  const configured = configuredValue("CAPTCHA_SECRET");
  if (configured) return configured;
  if (!globalState.__bandmaidCaptchaSecret) {
    globalState.__bandmaidCaptchaSecret = randomBytes(32).toString("hex");
  }
  return globalState.__bandmaidCaptchaSecret;
}

function cleanExpiredConsumed(): void {
  const now = Date.now();
  for (const [id, exp] of consumedCaptchas) {
    if (exp <= now) consumedCaptchas.delete(id);
  }
  if (consumedCaptchas.size > 20_000) {
    for (const id of consumedCaptchas.keys()) {
      consumedCaptchas.delete(id);
      if (consumedCaptchas.size <= 15_000) break;
    }
  }
}

function sign(content: string, secret: string): string {
  return createHmac("sha256", secret).update(content).digest("hex");
}

function hashAnswer(answer: string, secret: string): string {
  return createHmac("sha256", secret).update(answer.trim().toUpperCase()).digest("hex");
}

function randomItem<T>(items: readonly T[]): T {
  return items[randomInt(0, items.length)];
}

function generateRandomText(length = CAPTCHA_LENGTH): string {
  let result = "";
  for (let i = 0; i < length; i++) {
    result += CAPTCHA_CHARS[randomInt(0, CAPTCHA_CHARS.length)];
  }
  return result;
}

function generateCaptchaSvg(text: string): string {
  const width = 260;
  const height = 76;
  const chars = text.split("");

  // Colores sintonizados con la paleta de Band-Maid (dorados, marfil, carmesí sutil)
  const textColors = ["#f5cf68", "#e5c158", "#ffffff", "#e4e4e7", "#fca5a5", "#fde047"];
  const lineColors = ["rgba(212,175,55,0.45)", "rgba(239,68,68,0.35)", "rgba(228,228,231,0.35)", "rgba(161,161,170,0.4)"];
  const dotColors = ["#3f3f46", "#71717a", "#a1a1aa", "#d4af37"];

  // Líneas decorativas/ruido de fondo
  const noiseLines: string[] = [];
  for (let i = 0; i < 5; i++) {
    const x1 = randomInt(0, 30);
    const y1 = randomInt(10, height - 10);
    const cx = randomInt(80, 180);
    const cy = randomInt(5, height - 5);
    const x2 = randomInt(width - 30, width);
    const y2 = randomInt(10, height - 10);
    const color = randomItem(lineColors);
    const strokeWidth = (randomInt(14, 25) / 10).toFixed(1);
    noiseLines.push(`<path d="M${x1},${y1} Q${cx},${cy} ${x2},${y2}" stroke="${color}" stroke-width="${strokeWidth}" fill="none" stroke-linecap="round"/>`);
  }

  // Puntos/partículas de ruido
  const noiseDots: string[] = [];
  for (let i = 0; i < 40; i++) {
    const cx = randomInt(5, width - 5);
    const cy = randomInt(5, height - 5);
    const r = (randomInt(8, 20) / 10).toFixed(1);
    const color = randomItem(dotColors);
    const opacity = (randomInt(30, 85) / 100).toFixed(2);
    noiseDots.push(`<circle cx="${cx}" cy="${cy}" r="${r}" fill="${color}" opacity="${opacity}"/>`);
  }

  // Renderizado de cada carácter con posición, rotación, escala y fuente variadas
  const charSpacing = (width - 40) / chars.length;
  const renderedChars: string[] = [];

  chars.forEach((char, index) => {
    const x = Math.round(24 + index * charSpacing + randomInt(-3, 4));
    const y = Math.round(48 + randomInt(-5, 6));
    const angle = randomInt(-20, 21);
    const fontSize = randomInt(28, 34);
    const color = randomItem(textColors);
    const fontFamily = randomItem([
      "'Courier New', Courier, monospace",
      "'Arial Black', Impact, sans-serif",
      "Georgia, serif",
      "Trebuchet MS, sans-serif",
    ]);

    renderedChars.push(`
      <text
        x="${x}"
        y="${y}"
        font-family="${fontFamily}"
        font-size="${fontSize}"
        font-weight="800"
        fill="${color}"
        letter-spacing="2"
        transform="rotate(${angle}, ${x + 6}, ${y - 12})"
        filter="url(#captcha-blur-distortion)"
      >${char}</text>
    `);
  });

  // Línea transversal de interrupción al frente
  const strikeThroughX1 = randomInt(10, 35);
  const strikeThroughY1 = randomInt(25, 55);
  const strikeThroughX2 = randomInt(width - 35, width - 10);
  const strikeThroughY2 = randomInt(25, 55);
  const strikeColor = randomItem(lineColors);

  return `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" style="user-select:none;-webkit-user-select:none;">
      <defs>
        <!-- Filtro de distorsión con turbulencia fractal y desenfoque gaussiano suave (efecto borroso y ondeado) -->
        <filter id="captcha-blur-distortion" x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence type="fractalNoise" baseFrequency="0.038" numOctaves="2" result="noise" />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="3.8" xChannelSelector="R" yChannelSelector="G" result="distorted" />
          <feGaussianBlur in="distorted" stdDeviation="0.9" result="blurred" />
          <feMerge>
            <feMergeNode in="blurred" />
            <feMergeNode in="distorted" opacity="0.4" />
          </feMerge>
        </filter>
        <pattern id="captcha-grid" width="16" height="16" patternUnits="userSpaceOnUse">
          <path d="M 16 0 L 0 0 0 16" fill="none" stroke="#232328" stroke-width="0.7"/>
        </pattern>
      </defs>

      <!-- Fondo oscuro con textura y marco -->
      <rect width="${width}" height="${height}" fill="#141418" rx="2" />
      <rect width="${width}" height="${height}" fill="url(#captcha-grid)" opacity="0.65" />
      <rect width="${width}" height="${height}" fill="none" stroke="#2e2e36" stroke-width="1" rx="2" />

      <!-- Ruido de fondo -->
      ${noiseLines.join("\n")}
      ${noiseDots.join("\n")}

      <!-- Caracteres borrosos y distorsionados -->
      <g>
        ${renderedChars.join("\n")}
      </g>

      <!-- Línea frontal de interrupción -->
      <path d="M${strikeThroughX1},${strikeThroughY1} C${width / 3},${height - strikeThroughY1} ${(2 * width) / 3},${strikeThroughY2} ${strikeThroughX2},${strikeThroughY2}" stroke="${strikeColor}" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>
  `.trim();
}

export type TextCaptchaChallenge = {
  captchaToken: string;
  captchaImage: string;
  expiresInSeconds: number;
};

export function generateTextCaptcha(): TextCaptchaChallenge {
  cleanExpiredConsumed();
  const secret = getCaptchaSecret();
  const text = generateRandomText();
  const now = Date.now();
  const exp = now + CAPTCHA_TTL_MS;
  const id = randomBytes(16).toString("hex");

  const payload: CaptchaPayload = {
    id,
    iat: now,
    exp,
    hash: hashAnswer(text, secret),
  };

  const payloadB64 = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = sign(payloadB64, secret);
  const captchaToken = `${payloadB64}.${signature}`;

  const svg = generateCaptchaSvg(text);
  const captchaImage = `data:image/svg+xml;base64,${Buffer.from(svg, "utf-8").toString("base64")}`;

  return {
    captchaToken,
    captchaImage,
    expiresInSeconds: Math.floor(CAPTCHA_TTL_MS / 1000),
  };
}

export type VerifyCaptchaResult =
  | { success: true }
  | { success: false; code: "CAPTCHA_MISSING" | "CAPTCHA_EXPIRED" | "CAPTCHA_INVALID" | "CAPTCHA_REPLAYED" };

export function verifyTextCaptcha(token: unknown, answer: unknown): VerifyCaptchaResult {
  cleanExpiredConsumed();

  if (typeof token !== "string" || !token.trim() || typeof answer !== "string" || !answer.trim()) {
    return { success: false, code: "CAPTCHA_MISSING" };
  }

  const parts = token.split(".");
  if (parts.length !== 2) {
    return { success: false, code: "CAPTCHA_INVALID" };
  }

  const [payloadB64, providedSignature] = parts;
  const secret = getCaptchaSecret();
  const expectedSignature = sign(payloadB64, secret);

  if (!constantTimeMatch(expectedSignature, providedSignature)) {
    return { success: false, code: "CAPTCHA_INVALID" };
  }

  let payload: CaptchaPayload;
  try {
    payload = JSON.parse(Buffer.from(payloadB64, "base64url").toString("utf-8")) as CaptchaPayload;
  } catch {
    return { success: false, code: "CAPTCHA_INVALID" };
  }

  const now = Date.now();
  if (!payload.id || !payload.exp || !payload.hash || typeof payload.exp !== "number") {
    return { success: false, code: "CAPTCHA_INVALID" };
  }

  // Comprobar expiración
  if (now > payload.exp || now < payload.iat - 5000) {
    return { success: false, code: "CAPTCHA_EXPIRED" };
  }

  // Prevenir ataques de repetición: cada token solo se puede consumir UNA vez
  if (consumedCaptchas.has(payload.id)) {
    return { success: false, code: "CAPTCHA_REPLAYED" };
  }
  // Registrar inmediatamente como consumido
  consumedCaptchas.set(payload.id, payload.exp);

  // Validar respuesta del usuario en tiempo constante
  const computedHash = hashAnswer(answer, secret);
  if (!constantTimeMatch(computedHash, payload.hash)) {
    return { success: false, code: "CAPTCHA_INVALID" };
  }

  return { success: true };
}
