import "server-only";

import { createPrivateKey } from "node:crypto";
import { cert, getApps, initializeApp, type App } from "firebase-admin/app";
import { getAuth, type Auth } from "firebase-admin/auth";
import { getFirestore, type Firestore } from "firebase-admin/firestore";

export type FirebaseAdminServices = {
  app: App;
  auth: Auth;
  db: Firestore;
};

function configuredValue(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value && value.toUpperCase() !== "PENDIENDTE" ? value : undefined;
}

export function getFirebaseAdmin(): FirebaseAdminServices | null {
  const projectId = configuredValue("FIREBASE_ADMIN_PROJECT_ID");
  const clientEmail = configuredValue("FIREBASE_ADMIN_CLIENT_EMAIL");
  const privateKey = configuredValue("FIREBASE_ADMIN_PRIVATE_KEY")?.replace(/\\n/g, "\n");

  if (!projectId || !clientEmail || !privateKey) return null;

  try {
    createPrivateKey(privateKey);
    const app = getApps().find((candidate) => candidate.name === "bandmaid-admin") ?? initializeApp(
      { credential: cert({ projectId, clientEmail, privateKey }), projectId },
      "bandmaid-admin",
    );
    return { app, auth: getAuth(app), db: getFirestore(app) };
  } catch {
    return null;
  }
}
