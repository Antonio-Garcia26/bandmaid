import { FieldValue } from "firebase-admin/firestore";
import { NextResponse, type NextRequest } from "next/server";
import { getFirebaseAdmin } from "@/lib/firebase-admin";
import { getSessionUser } from "@/lib/security/auth";
import { validateMutation, type JsonRecord } from "@/lib/security/mutation";
import { enforceRateLimit } from "@/lib/security/rate-limit";
import { badRequest, jsonError, pendingResponse } from "@/lib/security/responses";
import { verifyTurnstile } from "@/lib/security/turnstile";
import { validateApiRequest } from "@/lib/security/request-guard";
import { validateHumanInteraction } from "@/lib/security/human-interaction";
import { examplePosts } from "@/lib/data";
import type { Post, PostCategory } from "@/lib/types";

const categories = new Set<PostCategory>(["general", "music", "live", "fan-art"]);
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

// Almacén en memoria para pruebas en entorno local sin Firestore configurado
const localDevPosts: Post[] = [...examplePosts];

function postFromData(id: string, data: JsonRecord): Post {
  const author = data.author && typeof data.author === "object" ? (data.author as JsonRecord) : {};
  return {
    id,
    title: typeof data.title === "string" ? data.title : "",
    body: typeof data.body === "string" ? data.body : "",
    category: categories.has(data.category as PostCategory) ? (data.category as PostCategory) : "general",
    author: {
      uid: typeof author.uid === "string" ? author.uid : "",
      displayName: typeof author.displayName === "string" ? author.displayName : "Fan de BAND-MAID",
    },
    createdAt: typeof data.createdAt === "string" ? data.createdAt : new Date(0).toISOString(),
    likes: typeof data.likes === "number" && Number.isFinite(data.likes) ? data.likes : 0,
  };
}

export async function GET(request: NextRequest) {
  const apiGuard = validateApiRequest(request);
  if (apiGuard) return apiGuard;

  const services = getFirebaseAdmin();
  if (!services) {
    if (process.env.NODE_ENV !== "production") {
      return Response.json({ posts: localDevPosts, configured: true }, { headers: { "Cache-Control": "no-store" } });
    }
    return pendingResponse("Firebase Firestore");
  }

  try {
    const snapshot = await services.db.collection("posts").orderBy("createdAt", "desc").limit(50).get();
    const posts = snapshot.docs.map((document) => postFromData(document.id, document.data() as JsonRecord));
    return Response.json({ posts, configured: true }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return jsonError("No se pudieron cargar las publicaciones.", 503, "FORUM_UNAVAILABLE");
  }
}

export async function POST(request: NextRequest) {
  const apiGuard = validateApiRequest(request);
  if (apiGuard) return apiGuard;

  const ipLimited = await enforceRateLimit(request, "posts-create");
  if (ipLimited) return ipLimited;

  const mutation = await validateMutation(request);
  if ("response" in mutation) return mutation.response;
  const { body } = mutation;

  // 1. Trampa Honeypot
  if (typeof body.website !== "string" || body.website.trim() !== "") {
    return jsonError("No se pudo validar el formulario.", 400, "BOT_REJECTED");
  }

  // 2. Validación de campos
  const id = typeof body.id === "string" ? body.id.trim() : "";
  const title = typeof body.title === "string" ? body.title.trim() : "";
  const content = typeof body.body === "string" ? body.body.trim() : "";
  const category = body.category;
  if (!uuidPattern.test(id) || title.length < 3 || title.length > 120 || content.length < 10 || content.length > 5000 || !categories.has(category as PostCategory)) {
    return badRequest("Revisa el título, el contenido y la categoría e inténtalo de nuevo.");
  }

  // 3. Verificación de comportamiento humano y telemetría (anti-scraping y anti-bots)
  const humanCheck = validateHumanInteraction(body.telemetry);
  if (humanCheck) return humanCheck;

  // 4. Usuario autenticado
  const user = await getSessionUser(request);
  if (!user) return jsonError("Inicia sesión para publicar.", 401, "AUTH_REQUIRED");

  const userLimited = await enforceRateLimit(request, "posts-create", user.uid, { includeIp: false });
  if (userLimited) return userLimited;

  // 5. Cloudflare Turnstile (solo si está configurado en el entorno)
  const turnstileSecret = process.env.TURNSTILE_SECRET_KEY?.trim();
  if (turnstileSecret && turnstileSecret.toUpperCase() !== "PENDIENDTE") {
    const turnstile = await verifyTurnstile(body.turnstileToken, "create-post", request);
    if (turnstile === "invalid") return jsonError("No se pudo verificar que eres una persona.", 400, "TURNSTILE_REJECTED");
  }

  const services = getFirebaseAdmin();
  if (!services) {
    if (process.env.NODE_ENV !== "production") {
      const createdAt = new Date().toISOString();
      const newPost: Post = {
        id,
        title,
        body: content,
        category: category as PostCategory,
        author: { uid: user.uid, displayName: user.displayName },
        createdAt,
        likes: 0,
      };
      localDevPosts.unshift(newPost);
      return NextResponse.json({ post: newPost }, { status: 201, headers: { "Cache-Control": "no-store" } });
    }
    return pendingResponse("Firebase Authentication y Firestore");
  }

  const ref = services.db.collection("posts").doc(id);
  try {
    const result = await services.db.runTransaction(async (transaction) => {
      const existing = await transaction.get(ref);
      if (existing.exists) {
        const data = existing.data() as JsonRecord;
        const author = data.author && typeof data.author === "object" ? (data.author as JsonRecord) : {};
        if (author.uid !== user.uid) return { conflict: true as const };
        return { post: postFromData(existing.id, data), conflict: false as const };
      }

      const createdAt = new Date().toISOString();
      const post: Post = {
        id,
        title,
        body: content,
        category: category as PostCategory,
        author: { uid: user.uid, displayName: user.displayName },
        createdAt,
        likes: 0,
      };
      transaction.create(ref, { ...post, author: post.author, createdAt, serverCreatedAt: FieldValue.serverTimestamp() });
      return { post, conflict: false as const };
    });

    if (result.conflict) return jsonError("No se pudo crear la publicación.", 409, "POST_ID_CONFLICT");
    return NextResponse.json({ post: result.post }, { status: 201, headers: { "Cache-Control": "no-store" } });
  } catch {
    return jsonError("No se pudo guardar la publicación. Inténtalo de nuevo.", 503, "POST_UNAVAILABLE");
  }
}
