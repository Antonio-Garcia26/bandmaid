export function configuredValue(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value && value.toUpperCase() !== "PENDIENDTE" ? value : undefined;
}

export function getAppOrigin(request?: Request): URL | null {
  const configured = configuredValue("APP_ORIGIN");
  if (configured) {
    try {
      const url = new URL(configured);
      if (url.protocol === "https:" || process.env.NODE_ENV !== "production") return url;
    } catch {
      return null;
    }
  }

  if (process.env.NODE_ENV === "production") return null;
  if (!request) return new URL("http://localhost:3000");

  try {
    const requestUrl = new URL(request.url);
    const hostHeader = request.headers.get("host");
    if (hostHeader) {
      const hostUrl = new URL(`${requestUrl.protocol}//${hostHeader}`);
      const hostname = hostUrl.hostname.toLowerCase();
      if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]") return hostUrl;
    }
    return requestUrl;
  } catch {
    return null;
  }
}

export function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

export function isConfigured(name: string): boolean {
  return Boolean(configuredValue(name));
}
