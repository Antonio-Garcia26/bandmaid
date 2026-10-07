"use client";

import { getApp, getApps, initializeApp, type FirebaseApp } from "firebase/app";
import { getAuth, type Auth } from "firebase/auth";
import { getFirestore, type Firestore } from "firebase/firestore";

export type FirebaseClient = {
  app: FirebaseApp;
  auth: Auth;
  db: Firestore;
};

const browserConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
};

const publicValue = (value: string | undefined) => {
  const normalized = value?.trim();
  return normalized && normalized.toUpperCase() !== "PENDIENDTE" ? normalized : undefined;
};

export function getFirebaseClient(): FirebaseClient | null {
  const apiKey = publicValue(browserConfig.apiKey);
  const authDomain = publicValue(browserConfig.authDomain);
  const projectId = publicValue(browserConfig.projectId);
  const appId = publicValue(browserConfig.appId);

  if (!apiKey || !authDomain || !projectId || !appId) return null;

  const app = getApps().length
    ? getApp()
    : initializeApp({
        apiKey,
        authDomain,
        projectId,
        appId,
        messagingSenderId: publicValue(browserConfig.messagingSenderId),
      });

  return { app, auth: getAuth(app), db: getFirestore(app) };
}

export function isFirebaseClientConfigured(): boolean {
  return Boolean(
    publicValue(browserConfig.apiKey) &&
      publicValue(browserConfig.authDomain) &&
      publicValue(browserConfig.projectId) &&
      publicValue(browserConfig.appId),
  );
}
