"use client";

import Image from "next/image";
import { ArrowUpRight, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { BandMember } from "@/lib/data";
import { Dialog } from "@/components/ui/Dialog";
import { useDynamicDomId } from "@/hooks/useDynamicDomId";

export function MemberSection() {
  const [members, setMembers] = useState<BandMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<BandMember | null>(null);
  const sectionRef = useRef<HTMLElement>(null);
  const { getId, getClass } = useDynamicDomId("band");

  useEffect(() => {
    let requested = false;

    const fetchMembers = async () => {
      if (requested) return;
      requested = true;

      try {
        const response = await fetch("/api/members", {
          method: "GET",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            Accept: "application/json",
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = (await response.json()) as { members?: BandMember[] };
        if (Array.isArray(data.members)) {
          setMembers(data.members);
          setError(null);
        } else {
          throw new Error("Formato inválido");
        }
      } catch {
        setError("No se pudieron cargar los datos de las integrantes.");
      } finally {
        setLoading(false);
      }
    };

    // 1. Carga diferida por scroll / visibilidad con IntersectionObserver
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          void fetchMembers();
          observer.disconnect();
        }
      },
      { rootMargin: "180px", threshold: 0.05 }
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    // 2. Respaldo por interacción física temprana (scroll o clic)
    const handleInteraction = () => {
      void fetchMembers();
      window.removeEventListener("scroll", handleInteraction);
      window.removeEventListener("pointerdown", handleInteraction);
    };

    window.addEventListener("scroll", handleInteraction, { passive: true, once: true });
    window.addEventListener("pointerdown", handleInteraction, { passive: true, once: true });

    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", handleInteraction);
      window.removeEventListener("pointerdown", handleInteraction);
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      className="members-section section-pad"
      id="miembros"
      aria-labelledby="members-title"
    >
      <div className="section-wrap">
        <div className="section-heading members-heading">
          <div>
            <p className="eyebrow"><span>01</span> LAS MAIDS</p>
            <h2 id="members-title" className="font-head section-title">
              Cinco voces.<br /><span>Un sonido.</span>
            </h2>
          </div>
          <p className="section-deck">
            Cada instrumento tiene su propia historia. Juntos, no dejan espacio para quedarse quietos.
          </p>
        </div>

        {error && (
          <div className="form-message form-message-error" role="alert" style={{ marginBottom: "20px" }}>
            <p>{error}</p>
          </div>
        )}

        <div className="member-grid">
          {loading ? (
            // Skeleton state: sin datos sensibles en SSR / HTML inicial
            [1, 2, 3, 4, 5].map((index) => (
              <article
                className={getClass("member-card member-skeleton", `skel-${index}`)}
                id={getId(`skeleton-${index}`)}
                key={index}
                aria-hidden="true"
              >
                <div className="member-card-button" style={{ cursor: "default", opacity: 0.75 }}>
                  <span className="member-photo-wrap skeleton-box" style={{ minHeight: "260px" }}>
                    <span className="member-index">0{index}</span>
                  </span>
                  <span
                    className="skeleton-line"
                    style={{ width: "65%", height: "22px", marginTop: "13px" }}
                  />
                  <span
                    className="skeleton-line"
                    style={{ width: "45%", height: "12px", marginTop: "8px" }}
                  />
                </div>
              </article>
            ))
          ) : (
            members.map((member, index) => (
              <article
                className={getClass("member-card", member.id)}
                id={getId(`card-${member.id}`)}
                key={member.id}
              >
                <button
                  className="member-card-button"
                  id={getId(`btn-${member.id}`)}
                  type="button"
                  onClick={() => setSelected(member)}
                  aria-label={`Ver perfil de ${member.name}`}
                >
                  <span className="member-photo-wrap">
                    <Image
                      src={member.image}
                      alt={`${member.name} en concierto`}
                      fill
                      sizes="(max-width: 640px) 45vw, (max-width: 1050px) 28vw, 225px"
                      className="member-photo"
                    />
                    <span className="member-index">0{index + 1}</span>
                    <span className="member-open" aria-hidden="true">
                      <ArrowUpRight size={18} />
                    </span>
                  </span>
                  <span className="member-name font-head">{member.name}</span>
                  <span className="member-role">{member.role}</span>
                </button>
              </article>
            ))
          )}
        </div>
        <div className="members-caption">
          <span>MIKU · SAIKI · KANAMI · AKANE · MISA</span>
          <span>MADE TO PLAY LOUD</span>
        </div>
      </div>

      <Dialog
        open={selected !== null}
        onClose={() => setSelected(null)}
        title={selected?.name ?? "Integrante de BAND-MAID"}
        eyebrow={selected?.role}
        className="member-dialog"
      >
        {selected && (
          <div className="member-detail" id={getId(`detail-${selected.id}`)}>
            <div className="member-detail-image">
              <Image
                src={selected.image}
                alt={`${selected.name} tocando en vivo`}
                fill
                sizes="(max-width: 700px) 80vw, 360px"
              />
            </div>
            <div className="member-detail-copy">
              <p className="member-detail-intro">{selected.intro}</p>
              <p>{selected.bio}</p>
              <p className="photo-credit">
                Foto:{" "}
                <a
                  href={selected.photoCredit.source}
                  target="_blank"
                  rel="noreferrer"
                >
                  {selected.photoCredit.author}{" "}
                  <ArrowUpRight size={13} aria-hidden="true" />
                </a>{" "}
                · CC BY-SA 4.0
              </p>
              <button
                className="text-action member-close-link"
                type="button"
                onClick={() => setSelected(null)}
              >
                Volver a la banda <X size={14} aria-hidden="true" />
              </button>
            </div>
          </div>
        )}
      </Dialog>
    </section>
  );
}
