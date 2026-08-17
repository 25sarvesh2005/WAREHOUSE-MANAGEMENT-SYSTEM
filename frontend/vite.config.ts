import tailwindcss from "@tailwindcss/vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import react from "@vitejs/plugin-react";
import { nitro } from "nitro/vite";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

type NitroBundlerConfig = {
  output?: {
    inlineDynamicImports?: boolean;
  };
};

export default defineConfig({
  css: {
    transformer: "lightningcss",
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    watch: {
      ignored: ["**/.output/**", "**/.wrangler/**", "**/dist/**"],
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    include: [
      "lucide-react",
      "@tanstack/react-router",
      "@tanstack/react-query",
      "@tanstack/query-core",
    ],
  },
  plugins: [
    tailwindcss(),
    tanstackStart({
      importProtection: {
        behavior: "error",
        client: {
          files: ["**/server/**"],
          specifiers: ["server-only"],
        },
      },
      client: { entry: "client" },
      server: { entry: "server" },
    }),
    nitro({
      defaultPreset:
        process.env["NITRO_PRESET"] || (process.env["VERCEL"] ? "vercel" : "cloudflare-module"),
      hooks: {
        "rollup:before": (_nitro: unknown, config: NitroBundlerConfig) => {
          delete config.output?.inlineDynamicImports;
        },
      },
    }),
    react(),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
    dedupe: [
      "react",
      "react-dom",
      "react/jsx-runtime",
      "react/jsx-dev-runtime",
      "@tanstack/react-query",
      "@tanstack/query-core",
    ],
    tsconfigPaths: true,
  },
});
