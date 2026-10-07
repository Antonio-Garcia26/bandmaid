"use client";

import { ArrowRight, Send } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import { ApiError, mutateJson, newPostId } from "@/lib/api-client";
import { useAuth } from "@/components/auth/AuthContext";
import { Turnstile } from "@/components/security/Turnstile";
import { Dialog } from "@/components/ui/Dialog";
import { categoryLabels } from "@/lib/data";
import type { Post, PostCategory } from "@/lib/types";

type CreatePostProps = {
  open: boolean;
  onClose: () => void;
  onOptimistic: (post: Post) => void;
  onConfirm: (postId: string, post: Post) => void;
  onRollback: (postId: string) => void;
};

type PostResponse = { post: Post };

export function CreatePost({ open, onClose, onOptimistic, onConfirm, onRollback }: CreatePostProps) {
  const auth = useAuth();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState<PostCategory>("general");
  const [turnstileToken, setTurnstileToken] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const honeypotRef = useRef<HTMLInputElement>(null);
  const postId = useRef<string | null>(null);

  const turnstileKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY?.trim();
  const canPost = Boolean(auth.user && auth.configured === true && turnstileKey && turnstileKey.toUpperCase() !== "PENDIENDTE");

  function closeComposer() {
    setTurnstileToken("");
    onClose();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!canPost || !auth.user || !turnstileToken || submitting) return;

    const id = postId.current ?? newPostId();
    postId.current = id;
    const optimisticPost: Post = {
      id,
      title: title.trim(),
      body: body.trim(),
      category,
      author: { uid: auth.user.uid, displayName: auth.user.displayName },
      createdAt: new Date().toISOString(),
      likes: 0,
      pending: true,
    };

    // Show the post before CSRF retrieval or the network request begins.
    onOptimistic(optimisticPost);
    setSubmitting(true);
    try {
      const response = await mutateJson<PostResponse>("/api/posts", {
        id,
        title: title.trim(),
        body: body.trim(),
        category,
        website: honeypotRef.current?.value ?? "",
        turnstileToken,
      });
      onConfirm(id, response.post);
      setTitle("");
      setBody("");
      setCategory("general");
      setError(null);
      postId.current = null;
      closeComposer();
    } catch (requestError) {
      onRollback(id);
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo conectar. Tu borrador sigue aquí; puedes intentarlo de nuevo.");
    } finally {
      setTurnstileToken("");
      setAttempt((value) => value + 1);
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onClose={closeComposer} title="Escribe para la comunidad." eyebrow="COMUNIDAD · NUEVA PUBLICACIÓN" className="create-post-dialog">
      {auth.user ? (
        <form className="create-post-form" onSubmit={handleSubmit}>
          {auth.configured === false && <p className="pending-note" role="status">PENDIENDTE: conectar Firebase para guardar publicaciones.</p>}
          <label className="field-label">
            Título
            <input className="plain-input" name="title" value={title} onChange={(event) => setTitle(event.target.value)} minLength={3} maxLength={120} required disabled={submitting} placeholder="¿Qué quieres compartir?" />
            <span className="field-count">{title.length}/120</span>
          </label>
          <label className="field-label">
            Tema
            <select className="plain-input category-select" value={category} onChange={(event) => setCategory(event.target.value as PostCategory)} disabled={submitting}>
              {(["general", "music", "live", "fan-art"] as const).map((item) => <option value={item} key={item}>{categoryLabels[item]}</option>)}
            </select>
          </label>
          <label className="field-label">
            Contenido
            <textarea className="plain-input post-body-input" name="body" value={body} onChange={(event) => setBody(event.target.value)} minLength={10} maxLength={5000} required disabled={submitting} placeholder="Comparte una idea, una recomendación o un momento que te haya marcado." />
            <span className="field-count">{body.length}/5000</span>
          </label>
          <input ref={honeypotRef} className="honeypot-field" name="website" type="text" autoComplete="off" tabIndex={-1} aria-hidden="true" />
          {open && <div className="turnstile-space"><Turnstile key={attempt} action="create-post" onToken={setTurnstileToken} /></div>}
          {error && <p className="form-message form-message-error" role="alert">{error}</p>}
          <div className="composer-footer">
            <p>Una publicación clara ayuda a que todas las maidiacs se sumen.</p>
            <button className="button button-red" type="submit" disabled={!canPost || !turnstileToken || submitting}>
              {submitting ? "Publicando…" : <>Publicar <Send size={15} aria-hidden="true" /></>}
            </button>
          </div>
          {auth.configured !== true && auth.configured !== false && auth.error && <button type="button" className="text-action" onClick={() => void auth.refresh()}>Reintentar conexión <ArrowRight size={14} aria-hidden="true" /></button>}
        </form>
      ) : (
        <div className="composer-login-prompt">
          <p>Inicia sesión para compartir algo con la comunidad.</p>
          {auth.configured === false && <p className="pending-note" role="status">PENDIENDTE: conectar Firebase para publicar.</p>}
        </div>
      )}
    </Dialog>
  );
}
