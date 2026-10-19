import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/api/*"],
      },
      {
        userAgent: [
          "curl",
          "python-requests",
          "python-urllib",
          "urllib",
          "httpx",
          "Scrapy",
          "wget",
          "PostmanRuntime",
          "HeadlessChrome",
          "Selenium",
          "Playwright",
          "Puppeteer",
          "GPTBot",
          "ChatGPT-User",
          "CCBot",
          "anthropic-ai",
          "Claude-Web",
        ],
        disallow: ["/"],
      },
    ],
  };
}
