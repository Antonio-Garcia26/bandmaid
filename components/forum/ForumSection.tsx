"use client";

import { ArrowRight, ArrowUpRight, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/auth/AuthContext";
import { CreatePost } from "@/components/forum/CreatePost";
import { Dialog } from "@/components/ui/Dialog";
import { ApiError, requestJson, type PostsResponse } from "@/lib/api-client";
import { categoryLabels, examplePosts } from "@/lib/data";
import type { Post, PostCategory } from "@/lib/types";

type ForumSectionProps = { onOpenAuth: (mode?: "login" | "register") => void };
type LoadState = "loading" | "ready" | "demo" | "error";

const categories: Array<PostCategory | "all"> = ["all", "general", "music", "live", "fan-art"];

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Fecha no disponible";
  return new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(date);
}

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("") || "BM";
}

export function ForumSection({ onOpenAuth }: ForumSectionProps) {
  const auth = useAuth();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState("");
  const [reloadCount, setReloadCount] = useState(0);
  const [category, setCategory] = useState<PostCategory | "all">("all");
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState<"latest" | "popular">("latest");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);

  useEffect(() => {
    let cancelled = false;
    requestJson<PostsResponse>("/api/posts")
      .then((response) => {
        if (cancelled) return;
        setPosts(response.posts);
        setLoadState("ready");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.code === "CONFIG_PENDING") {
          setPosts(examplePosts);
          setLoadState("demo");
          return;
        }
        setLoadError(error instanceof ApiError ? error.message : "No se pudo conectar para cargar las publicaciones.");
        setLoadState("error");
      });
    return () => { cancelled = true; };
  }, [reloadCount]);

  function retryPosts() {
    setLoadError("");
    setLoadState("loading");
    setReloadCount((count) => count + 1);
  }

  const visiblePosts = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("es-MX");
    const filtered = posts.filter((post) => {
      const matchesCategory = category === "all" || post.category === category;
      const matchesQuery = !normalizedQuery || `${post.title} ${post.body}`.toLocaleLowerCase("es-MX").includes(normalizedQuery);
      return matchesCategory && matchesQuery;
    });
    return filtered.sort((first, second) => {
      if (sortBy === "popular" && first.likes !== second.likes) return second.likes - first.likes;
      return new Date(second.createdAt).getTime() - new Date(first.createdAt).getTime();
    });
  }, [posts, category, query, sortBy]);

  function openComposer() {
    if (!auth.user) {
      onOpenAuth("login");
      return;
    }
    setCreateOpen(true);
  }

  function addOptimistic(post: Post) {
    setCategory("all");
    setQuery("");
    setSortBy("latest");
    setPosts((current) => [post, ...current]);
    setCreateOpen(false);
  }

  function confirmPost(postId: string, savedPost: Post) {
    setPosts((current) => current.map((post) => post.id === postId ? { ...savedPost, pending: false } : post));
  }

  function rollbackPost(postId: string) {
    setPosts((current) => current.filter((post) => post.id !== postId));
    setCreateOpen(true);
  }

  return (
    <section className="forum-section section-pad" id="comunidad" aria-labelledby="forum-title">
      <div className="section-wrap">
        <div className="section-heading forum-heading">
          <div>
            <p className="eyebrow"><span>03</span> NUESTRA COMUNIDAD</p>
            <h2 id="forum-title" className="font-head section-title">La comunidad,<br /><span>a todo volumen.</span></h2>
          </div>
          <button className="button button-outline forum-create-top" type="button" onClick={openComposer}>
            Nueva publicación <ArrowRight size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="forum-layout">
          <div className="forum-main">
            {loadState === "demo" && (
              <div className="example-banner" role="status">
                <span className="example-dot" />
                <p><strong>Publicaciones de ejemplo</strong> · PENDIENDTE: conectar Firebase para ver el foro.</p>
              </div>
            )}

            <div className="forum-tools">
              <div className="category-tabs" role="tablist" aria-label="Filtrar publicaciones por tema">
                {categories.map((item) => (
                  <button key={item} className={category === item ? "category-tab active" : "category-tab"} type="button" role="tab" aria-selected={category === item} onClick={() => setCategory(item)}>
                    {categoryLabels[item]}
                  </button>
                ))}
              </div>
              <div className="forum-filter-row">
                <label className="forum-search">
                  <Search size={17} aria-hidden="true" />
                  <span className="visually-hidden">Buscar por título o contenido</span>
                  <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar en la comunidad" />
                </label>
                <label className="sort-control">
                  <span className="visually-hidden">Ordenar publicaciones</span>
                  <select value={sortBy} onChange={(event) => setSortBy(event.target.value as "latest" | "popular")}>
                    <option value="latest">Más recientes</option>
                    <option value="popular">Más populares</option>
                  </select>
                </label>
              </div>
            </div>

            {loadState === "loading" && <div className="forum-state" role="status"><span className="loading-mark" /> Cargando publicaciones…</div>}
            {loadState === "error" && (
              <div className="forum-state forum-state-error" role="alert">
                <p>{loadError}</p>
                <button className="text-action" type="button" onClick={retryPosts}>Intentar de nuevo <ArrowRight size={14} aria-hidden="true" /></button>
              </div>
            )}
            {loadState !== "loading" && loadState !== "error" && visiblePosts.length === 0 && (
              <div className="forum-state empty-state"><p>{posts.length ? "No hay publicaciones con ese filtro." : "Todavía no hay publicaciones. Puedes abrir la conversación."}</p>{posts.length === 0 && <button className="text-action" type="button" onClick={openComposer}>Escribir la primera <ArrowRight size={14} aria-hidden="true" /></button>}</div>
            )}
            {loadState !== "loading" && loadState !== "error" && visiblePosts.length > 0 && (
              <div className="post-list" aria-live="polite">
                {visiblePosts.map((post) => (
                  <article className="post-row" key={post.id}>
                    <div className="post-avatar" aria-hidden="true">{initials(post.author.displayName)}</div>
                    <div className="post-row-main">
                      <div className="post-meta"><span className={`post-category post-category-${post.category}`}>{categoryLabels[post.category]}</span><span>{formatDate(post.createdAt)}</span>{post.pending && <span className="post-pending">Guardando…</span>}{loadState === "demo" && <span className="post-example">EJEMPLO</span>}</div>
                      <button type="button" className="post-title-button font-head" onClick={() => setSelectedPost(post)}>{post.title}</button>
                      <p className="post-excerpt">{post.body}</p>
                      <span className="post-author">Por {post.author.displayName}</span>
                    </div>
                    <button className="post-open" type="button" onClick={() => setSelectedPost(post)} aria-label={`Leer publicación: ${post.title}`}><ArrowUpRight size={18} aria-hidden="true" /></button>
                  </article>
                ))}
              </div>
            )}
          </div>

          <aside className="community-aside">
            <p className="eyebrow eyebrow-light"><span>MAIDIACS</span></p>
            <h3 className="font-head">Tu lugar entre<br />las maidiacs.</h3>
            <p>Comparte una canción, una idea o ese riff que aún traes en la cabeza.</p>
            <button className="button button-red aside-button" type="button" onClick={() => auth.user ? setCreateOpen(true) : onOpenAuth("register")}>
              {auth.user ? "Escribir una publicación" : "Únete a la conversación"} <ArrowRight size={16} aria-hidden="true" />
            </button>
            <div className="house-rules">
              <p className="eyebrow eyebrow-light">ACUERDOS DE CASA</p>
              <ul>
                <li>Hablemos con respeto.</li>
                <li>Créditos para el trabajo ajeno.</li>
                <li>El espacio es para fans y música.</li>
              </ul>
            </div>
            {!auth.user && <button type="button" className="aside-login-link" onClick={() => onOpenAuth("login")}>¿Ya tienes cuenta? Inicia sesión <ArrowUpRight size={14} aria-hidden="true" /></button>}
          </aside>
        </div>
      </div>

      <CreatePost
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onOptimistic={addOptimistic}
        onConfirm={confirmPost}
        onRollback={rollbackPost}
      />
      <Dialog open={selectedPost !== null} onClose={() => setSelectedPost(null)} title={selectedPost?.title ?? "Publicación"} eyebrow={selectedPost ? `${categoryLabels[selectedPost.category]} · ${formatDate(selectedPost.createdAt)}` : "COMUNIDAD"} className="post-detail-dialog">
        {selectedPost && (
          <article className="post-detail-content">
            <p className="post-detail-byline">Por {selectedPost.author.displayName}{selectedPost.pending && <span className="post-pending"> · Guardando…</span>}</p>
            <p className="post-detail-body">{selectedPost.body}</p>
          </article>
        )}
      </Dialog>
    </section>
  );
}
