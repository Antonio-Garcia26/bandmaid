import type { Post, PostCategory } from "@/lib/types";

export type BandMember = {
  id: string;
  name: string;
  role: string;
  image: string;
  intro: string;
  bio: string;
  photoCredit: { author: string; source: string };
};

export const bandMembers: BandMember[] = [
  {
    id: "miku",
    name: "Miku Kobato",
    role: "Guitarra · voz",
    image: "/images/miku.jpg",
    intro: "La voz que abrió la puerta del maid café al rock más feroz.",
    bio: "Fundadora de BAND-MAID, Miku une su guitarra rítmica con una voz que cambia de registro sin perder su personalidad. Su idea convirtió una estética de maid café en el punto de partida de una banda de hard rock con identidad propia.",
    photoCredit: { author: "DragonFury", source: "https://commons.wikimedia.org/wiki/File:Band-Maid_Miku_Frankfurt_050626.jpg" },
  },
  {
    id: "saiki",
    name: "Saiki",
    role: "Voz principal",
    image: "/images/saiki.jpg",
    intro: "Una voz potente y elegante al frente del escenario.",
    bio: "Saiki es la vocalista principal de la banda. Su interpretación, precisa y llena de carácter, guía los cambios de energía que hacen reconocible el sonido de BAND-MAID.",
    photoCredit: { author: "DragonFury", source: "https://commons.wikimedia.org/wiki/File:Band-Maid_Saiki_Frankfurt_050626.jpg" },
  },
  {
    id: "kanami",
    name: "Kanami",
    role: "Guitarra principal · composición",
    image: "/images/kanami.jpg",
    intro: "Riffs, solos y canciones que no se quedan quietas.",
    bio: "Kanami toca la guitarra principal y compone gran parte del repertorio. Sus arreglos enlazan melodías brillantes con pasajes de hard rock de gran precisión.",
    photoCredit: { author: "DragonFury", source: "https://commons.wikimedia.org/wiki/File:Band-Maid_Kanami_Frankfurt_050626.jpg" },
  },
  {
    id: "akane",
    name: "Akane",
    role: "Batería",
    image: "/images/akane.jpg",
    intro: "El pulso contundente que empuja cada canción.",
    bio: "Akane está en la batería y sostiene la potencia rítmica del grupo. Su ejecución combina fuerza con cambios de compás y detalles que invitan a volver a escuchar.",
    photoCredit: { author: "DragonFury", source: "https://commons.wikimedia.org/wiki/File:Band-Maid_Akane_Frankfurt_050626.jpg" },
  },
  {
    id: "misa",
    name: "MISA",
    role: "Bajo",
    image: "/images/misa.jpg",
    intro: "Líneas profundas, groove y una presencia inconfundible.",
    bio: "MISA toca el bajo y forma la base grave del sonido de la banda. Sus líneas mantienen el groove mientras la música se mueve entre melodías pop y riffs de rock.",
    photoCredit: { author: "Crisco 1492", source: "https://commons.wikimedia.org/wiki/File:Band-Maid_performing_at_Saint_Andrew%27s_Hall,_Detroit,_2023-05-24_10.jpg" },
  },
];

export type BandVideo = { id: string; title: string; note: string };

export const bandVideos: BandVideo[] = [
  { id: "yfORoQIqB3E", title: "HATE?", note: "HATE? Official Live Video from 10TH ANNIVERSARY TOUR FINAL in YOKOHAMA ARENA (Nov. 26,2023)" },
  { id: "dHKn6y2a5tg", title: "Ready to Rock / Live at CENTRAL26", note: "Performance footage from the urban music festival CENTRAL26, held in Yokohama in April, available for a limited time only." },
  { id: "FHpuEqMAcDg", title: "FREEDOM ", note: "Freedom OKYU-JI (live) video from WORLD DOMINATION TOUR 【進化 at LINE CUBE SHIBUYA." },
  { id: "oWQpbAmfZLE", title: "WITHOUT HOLDING BACK", note: "Official Live Video from BAND-MAID TOUR 2025 FINAL TOKYO GARDEN THEATER" },
];

export const categoryLabels: Record<PostCategory | "all", string> = {
  all: "Todo",
  general: "General",
  music: "Música",
  live: "En vivo",
  "fan-art": "Fan art",
};

// Shown only when the API explicitly reports CONFIG_PENDING. These are examples, not forum records.
export const examplePosts: Post[] = [
  {
    id: "demo-first-song",
    title: "¿Qué canción te hizo quedarte?",
    body: "La primera que escuché fue Choose me, pero el riff de DOMINATION fue el momento en que supe que iba a seguir escuchándolas.",
    category: "music",
    author: { uid: "example", displayName: "Nora" },
    createdAt: "2026-06-12T17:30:00.000Z",
    likes: 0,
  },
  {
    id: "demo-live-memory",
    title: "Ese segundo antes del primer riff",
    body: "¿También se quedan en silencio cuando se apagan las luces? El primer golpe de batería en vivo siempre se siente enorme.",
    category: "live",
    author: { uid: "example", displayName: "Leo" },
    createdAt: "2026-06-08T21:15:00.000Z",
    likes: 0,
  },
  {
    id: "demo-listening",
    title: "Una recomendación para empezar",
    body: "Si alguien quiere compartir la banda con una amistad, ¿qué tres canciones pondrían primero? Yo empezaría con Choose me, DICE y Sense.",
    category: "general",
    author: { uid: "example", displayName: "Majo" },
    createdAt: "2026-06-01T14:05:00.000Z",
    likes: 0,
  },
];

export const imageCredits = [
  { author: "DragonFury", source: "https://commons.wikimedia.org/wiki/File:BandMaid_Frankfurt_050626.png", label: "BAND-MAID · Frankfurt, 2026" },
  { author: "DragonFury", source: "https://commons.wikimedia.org/wiki/File:Band-Maid_Miku_Frankfurt_050626.jpg", label: "Miku · Frankfurt" },
  { author: "DragonFury", source: "https://commons.wikimedia.org/wiki/File:Band-Maid_Saiki_Frankfurt_050626.jpg", label: "Saiki · Frankfurt" },
  { author: "DragonFury", source: "https://commons.wikimedia.org/wiki/File:Band-Maid_Kanami_Frankfurt_050626.jpg", label: "Kanami · Frankfurt" },
  { author: "DragonFury", source: "https://commons.wikimedia.org/wiki/File:Band-Maid_Akane_Frankfurt_050626.jpg", label: "Akane · Frankfurt" },
  { author: "Crisco 1492", source: "https://commons.wikimedia.org/wiki/File:Band-Maid_performing_at_Saint_Andrew%27s_Hall,_Detroit,_2023-05-24_10.jpg", label: "MISA · Detroit" },
  { author: "Crisco 1492", source: "https://commons.wikimedia.org/wiki/File:Band-Maid_performing_at_Saint_Andrew%27s_Hall,_Detroit,_2023-05-24_04.jpg", label: "BAND-MAID · Detroit" },
  { author: "Sergio Jesús Martínez Díaz", source: "https://commons.wikimedia.org/wiki/File:BAND-MAID_(left_to_right;_MISA,_Kobato_Miku,_Akane,_Saiki,_Kanami)_at_SALA_show_in_Mexico_City_in_2016.jpg", label: "BAND-MAID · Ciudad de México" },
];
