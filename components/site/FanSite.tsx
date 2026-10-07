"use client";

import Image from "next/image";
import { ArrowDownRight, ArrowRight, ArrowUpRight, Menu, Play, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { AuthModal } from "@/components/auth/AuthModal";
import { AuthProvider, useAuth } from "@/components/auth/AuthContext";
import { ForumSection } from "@/components/forum/ForumSection";
import { MemberSection } from "@/components/site/MemberSection";
import { VideoSection } from "@/components/site/VideoSection";
import { ApiError } from "@/lib/api-client";
import { bandVideos, imageCredits, type BandVideo } from "@/lib/data";

const navigation = [
  { id: "inicio", label: "Inicio" },
  { id: "miembros", label: "La banda" },
  { id: "videos", label: "Videos" },
  { id: "comunidad", label: "Comunidad" },
];

function FanSiteContent() {
  const auth = useAuth();
  const [activeSection, setActiveSection] = useState("inicio");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [selectedVideo, setSelectedVideo] = useState<BandVideo | null>(null);
  const [signOutError, setSignOutError] = useState("");
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    const sections = navigation.map(({ id }) => document.getElementById(id)).filter((section): section is HTMLElement => section !== null);
    const observer = new IntersectionObserver((entries) => {
      const active = entries.filter((entry) => entry.isIntersecting).sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
      if (active?.target instanceof HTMLElement) setActiveSection(active.target.id);
    }, { rootMargin: "-22% 0px -66% 0px", threshold: [0, 0.1, 0.3, 0.6] });
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  const openAuth = useCallback((mode: "login" | "register" = "login") => {
    setAuthMode(mode);
    setAuthOpen(true);
    setMobileOpen(false);
  }, []);

  const handleSignOut = async () => {
    if (signingOut) return;
    setSignOutError("");
    setSigningOut(true);
    try {
      await auth.signOut();
    } catch (error) {
      setSignOutError(error instanceof ApiError ? error.message : "No se pudo conectar para cerrar sesión.");
    } finally {
      setSigningOut(false);
    }
  };

  const closeMobileMenu = () => setMobileOpen(false);
  const featuredVideo = bandVideos[0];

  return (
    <>
      <a className="skip-link" href="#contenido">Saltar al contenido</a>
      <div className="microbar">
        <span>DE JAPÓN. PARA EL MUNDO.</span>
        <span className="microbar-center">HARD ROCK · SOFT SPOT FOR THE MAIDS</span>
        <span>UNOFFICIAL FAN COMMUNITY</span>
      </div>

      <header className="site-header">
        <div className="header-inner page-wrap">
          <a className="wordmark" href="#inicio" aria-label="BAND-MAID World Domination Club, inicio" onClick={closeMobileMenu}>
            <span className="wordmark-main font-head">BAND<span className="wordmark-dash">—</span>MAID<span className="wordmark-mark">♪</span></span>
            <span className="wordmark-sub">WORLD DOMINATION CLUB</span>
          </a>

          <button className="mobile-menu-button icon-button" type="button" onClick={() => setMobileOpen((open) => !open)} aria-expanded={mobileOpen} aria-controls="main-navigation" aria-label={mobileOpen ? "Cerrar menú" : "Abrir menú"}>
            {mobileOpen ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
          </button>

          <nav id="main-navigation" className={mobileOpen ? "main-nav mobile-open" : "main-nav"} aria-label="Navegación principal">
            <div className="nav-links">
              {navigation.map((item) => (
                <a key={item.id} className={activeSection === item.id ? "nav-link active" : "nav-link"} href={`#${item.id}`} aria-current={activeSection === item.id ? "page" : undefined} onClick={closeMobileMenu}>{item.label}</a>
              ))}
            </div>
            <div className="nav-actions">
              {auth.user ? (
                <>
                  <span className="nav-greeting">Hola, {auth.user.displayName.split(" ")[0]}</span>
                  <button className="nav-login" type="button" onClick={() => void handleSignOut()} disabled={signingOut}>{signingOut ? "Cerrando…" : "Cerrar sesión"}</button>
                </>
              ) : (
                <>
                  <button className="nav-login" type="button" onClick={() => openAuth("login")}>Iniciar sesión</button>
                  <button className="button button-red nav-join" type="button" onClick={() => openAuth("register")}>Únete al club <ArrowRight size={15} aria-hidden="true" /></button>
                </>
              )}
            </div>
          </nav>
        </div>
        {signOutError && <p className="signout-error page-wrap" role="alert">{signOutError}</p>}
      </header>

      <main id="contenido">
        <section className="hero-section page-wrap" id="inicio" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow hero-eyebrow"><span className="eyebrow-star">✳</span> WELCOME HOME, MAIDIACS</p>
            <h1 id="hero-title" className="font-head hero-title">WORLD<br /><span>DOMINATION</span><br /><span className="hero-lastline">STARTS HERE<span className="hero-period">.</span></span></h1>
            <p className="hero-japanese" lang="ja">世界征服 <span>— world domination</span></p>
            <p className="hero-description">Cinco músicas. Un sonido imparable. Un lugar para quienes lo viven.</p>
            <div className="hero-actions">
              <a className="button button-red" href="#miembros">Explorar la banda <ArrowRight size={16} aria-hidden="true" /></a>
              <a className="hero-video-link" href="#videos"><span className="hero-play"><Play size={12} fill="currentColor" aria-hidden="true" /></span> Ver videos</a>
            </div>
          </div>

          <div className="hero-visual">
            <div className="hero-photo-frame">
              <Image src="/images/band-stage.png" alt="BAND-MAID tocando en directo en Frankfurt" fill priority sizes="(max-width: 850px) 100vw, 58vw" className="hero-photo" />
              <span className="hero-photo-index">BM — 05</span>
              <span className="hero-vertical-caption">BAND-MAID / LIVE &amp; LOUD</span>
              <div className="hero-sticker"><span>MAID IN JAPAN</span><strong>LOUD<br />EVERYWHERE</strong><span className="sticker-star">✳</span></div>
            </div>
            <div className="hero-image-caption"><span>FRANKFURT · 05.06.2026</span><span>FIVE MEMBERS / ONE MISSION</span></div>
          </div>

          <div className="hero-stats" aria-label="Datos de la comunidad">
            <div><strong>05</strong><span>INTEGRANTES</span></div>
            <div><strong>01</strong><span>COMUNIDAD</span></div>
            <div><strong>∞</strong><span>DECIBELES</span></div>
            <a href="#comunidad" aria-label="Desplazarse a la comunidad"><ArrowDownRight size={25} aria-hidden="true" /></a>
          </div>
        </section>

        <div className="ticker-band" aria-label="Hard rock. Soft spot for the maids. World domination.">
          <div className="ticker-inner"><span>HARD ROCK</span><i>✳</i><span>SOFT SPOT FOR THE MAIDS</span><i>✳</i><span>WORLD DOMINATION</span><i>✳</i><span>HARD ROCK</span><i>✳</i></div>
        </div>

        <section className="editorial-strip section-pad" aria-label="La música y la comunidad">
          <div className="section-wrap editorial-grid">
            <div className="editorial-community">
              <p className="eyebrow"><span>FAN TO FAN</span></p>
              <h2 className="font-head">La música fue el principio.<br /><span>La comunidad es el hogar.</span></h2>
              <p>Recomendaciones, recuerdos y conversaciones entre fans. Pasa, aquí siempre hay lugar.</p>
              <a className="text-action" href="#comunidad">Conoce la comunidad <ArrowRight size={15} aria-hidden="true" /></a>
            </div>
            <div className="editorial-feature">
              <button className="editorial-video-poster" type="button" onClick={() => setSelectedVideo(featuredVideo)} aria-label={`Reproducir ${featuredVideo.title}`}>
                {/* eslint-disable @next/next/no-img-element */}
                <img src={`https://i.ytimg.com/vi/${featuredVideo.id}/hqdefault.jpg`} alt="Miniatura del video Choose me" loading="lazy" />
                {/* eslint-enable @next/next/no-img-element */}
                <span className="editorial-play"><Play size={15} fill="currentColor" aria-hidden="true" /></span>
                <span className="editorial-video-label">VIDEO DESTACADO · 01</span>
              </button>
              <div className="editorial-video-title"><span className="font-head">Choose me</span><button type="button" aria-label="Reproducir Choose me" onClick={() => setSelectedVideo(featuredVideo)}><ArrowUpRight size={18} aria-hidden="true" /></button></div>
            </div>
          </div>
        </section>

        <MemberSection />
        <VideoSection selectedVideo={selectedVideo} onSelectVideo={setSelectedVideo} />
        <ForumSection onOpenAuth={openAuth} />
      </main>

      <footer className="site-footer">
        <div className="section-wrap footer-inner">
          <div className="footer-main">
            <div className="footer-brand-block">
              <a className="footer-wordmark font-head" href="#inicio">BAND<span>—</span>MAID<span className="wordmark-mark">♪</span></a>
              <p>WORLD DOMINATION CLUB<br />UNOFFICIAL FAN COMMUNITY</p>
            </div>
            <div className="footer-disclaimer">
              <p>Proyecto escolar de fans, sin afiliación con BAND-MAID ni sus representantes. Todo el respeto y los créditos pertenecen a sus titulares.</p>
              <a href="https://bandmaid.tokyo/" target="_blank" rel="noreferrer">Sitio oficial de BAND-MAID <ArrowUpRight size={13} aria-hidden="true" /></a>
            </div>
            <div className="footer-back"><a href="#inicio">Volver arriba <ArrowUpRight size={16} aria-hidden="true" /></a></div>
          </div>
          <div className="footer-credits">
            <p className="eyebrow eyebrow-light">CRÉDITOS FOTOGRÁFICOS · CC BY-SA 4.0</p>
            <div className="credit-links">
              {imageCredits.map((credit) => <a key={credit.label} href={credit.source} target="_blank" rel="noreferrer">{credit.label} · {credit.author} <ArrowUpRight size={11} aria-hidden="true" /></a>)}
              <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer">Licencia Creative Commons BY-SA 4.0 <ArrowUpRight size={11} aria-hidden="true" /></a>
            </div>
          </div>
          <div className="footer-bottom"><span>HECHO CON RESPETO Y MUCHO VOLUMEN.</span><span>© 2026 · FAN PROJECT</span></div>
        </div>
      </footer>

      {authOpen && <AuthModal open onClose={() => setAuthOpen(false)} initialMode={authMode} />}
    </>
  );
}

export function FanSite() {
  return <AuthProvider><FanSiteContent /></AuthProvider>;
}
