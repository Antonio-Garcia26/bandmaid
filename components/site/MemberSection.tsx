"use client";

import Image from "next/image";
import { ArrowUpRight, X } from "lucide-react";
import { useState } from "react";
import { bandMembers, type BandMember } from "@/lib/data";
import { Dialog } from "@/components/ui/Dialog";

export function MemberSection() {
  const [selected, setSelected] = useState<BandMember | null>(null);

  return (
    <section className="members-section section-pad" id="miembros" aria-labelledby="members-title">
      <div className="section-wrap">
        <div className="section-heading members-heading">
          <div>
            <p className="eyebrow"><span>01</span> LAS MAIDS</p>
            <h2 id="members-title" className="font-head section-title">Cinco voces.<br /><span>Un sonido.</span></h2>
          </div>
          <p className="section-deck">Cada instrumento tiene su propia historia. Juntos, no dejan espacio para quedarse quietos.</p>
        </div>

        <div className="member-grid">
          {bandMembers.map((member, index) => (
            <article className="member-card" key={member.id}>
              <button className="member-card-button" type="button" onClick={() => setSelected(member)} aria-label={`Ver perfil de ${member.name}`}>
                <span className="member-photo-wrap">
                  <Image src={member.image} alt={`${member.name} en concierto`} fill sizes="(max-width: 640px) 45vw, (max-width: 1050px) 28vw, 225px" className="member-photo" />
                  <span className="member-index">0{index + 1}</span>
                  <span className="member-open" aria-hidden="true"><ArrowUpRight size={18} /></span>
                </span>
                <span className="member-name font-head">{member.name}</span>
                <span className="member-role">{member.role}</span>
              </button>
            </article>
          ))}
        </div>
        <div className="members-caption"><span>MIKU · SAIKI · KANAMI · AKANE · MISA</span><span>MADE TO PLAY LOUD</span></div>
      </div>

      <Dialog open={selected !== null} onClose={() => setSelected(null)} title={selected?.name ?? "Integrante de BAND-MAID"} eyebrow={selected?.role} className="member-dialog">
        {selected && (
          <div className="member-detail">
            <div className="member-detail-image">
              <Image src={selected.image} alt={`${selected.name} tocando en vivo`} fill sizes="(max-width: 700px) 80vw, 360px" />
            </div>
            <div className="member-detail-copy">
              <p className="member-detail-intro">{selected.intro}</p>
              <p>{selected.bio}</p>
              <p className="photo-credit">Foto: <a href={selected.photoCredit.source} target="_blank" rel="noreferrer">{selected.photoCredit.author} <ArrowUpRight size={13} aria-hidden="true" /></a> · CC BY-SA 4.0</p>
              <button className="text-action member-close-link" type="button" onClick={() => setSelected(null)}>Volver a la banda <X size={14} aria-hidden="true" /></button>
            </div>
          </div>
        )}
      </Dialog>
    </section>
  );
}
