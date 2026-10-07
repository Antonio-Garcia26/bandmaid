"use client";

import { ArrowUpRight, Play } from "lucide-react";
import { bandVideos, type BandVideo } from "@/lib/data";
import { Dialog } from "@/components/ui/Dialog";

type VideoSectionProps = {
  selectedVideo: BandVideo | null;
  onSelectVideo: (video: BandVideo | null) => void;
};

export function VideoSection({ selectedVideo, onSelectVideo }: VideoSectionProps) {
  return (
    <section className="videos-section section-pad" id="videos" aria-labelledby="videos-title">
      <div className="section-wrap">
        <div className="section-heading videos-heading">
          <div>
            <p className="eyebrow eyebrow-light"><span>02</span> SUBE EL VOLUMEN</p>
            <h2 id="videos-title" className="font-head section-title">Música para<br /><span>romper el silencio.</span></h2>
          </div>
          <p className="section-deck">Videos del canal oficial de BAND-MAID. Elige uno y dale play desde esta página.</p>
        </div>

        <div className="video-grid">
          {bandVideos.map((video, index) => (
            <article className="video-card" key={video.id}>
              <button className="video-poster" type="button" onClick={() => onSelectVideo(video)} aria-label={`Reproducir ${video.title}`}>
                {/* YouTube serves this thumbnail; Next Image remote hosts are intentionally not configured. */}
                {/* eslint-disable @next/next/no-img-element */}
                <img src={`https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`} alt={`Miniatura del video ${video.title}`} loading="lazy" />
                {/* eslint-enable @next/next/no-img-element */}
                <span className="video-number">0{index + 1}</span>
                <span className="video-play" aria-hidden="true"><Play size={20} fill="currentColor" /></span>
              </button>
              <div className="video-card-copy">
                <div><h3 className="font-head">{video.title}</h3><p>{video.note}</p></div>
                <a href={`https://www.youtube.com/watch?v=${video.id}`} target="_blank" rel="noreferrer" aria-label={`Ver ${video.title} en YouTube`}><ArrowUpRight size={18} aria-hidden="true" /></a>
              </div>
            </article>
          ))}
        </div>
        <p className="video-credit-line">Los videos y sus derechos pertenecen a BAND-MAID y sus titulares. Los embeds se cargan al elegir reproducir.</p>
      </div>

      <Dialog open={selectedVideo !== null} onClose={() => onSelectVideo(null)} title={selectedVideo?.title ?? "Video de BAND-MAID"} eyebrow="VIDEO OFICIAL · YOUTUBE" className="video-dialog">
        {selectedVideo && (
          <div className="video-dialog-content">
            <div className="video-frame">
              <iframe
                key={selectedVideo.id}
                src={`https://www.youtube-nocookie.com/embed/${selectedVideo.id}?autoplay=1`}
                title={`${selectedVideo.title} — BAND-MAID`}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                referrerPolicy="strict-origin-when-cross-origin"
                allowFullScreen
              />
            </div>
            <a className="text-action video-fallback" href={`https://www.youtube.com/watch?v=${selectedVideo.id}`} target="_blank" rel="noreferrer">Abrir en YouTube <ArrowUpRight size={15} aria-hidden="true" /></a>
          </div>
        )}
      </Dialog>
    </section>
  );
}
