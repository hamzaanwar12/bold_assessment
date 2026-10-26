/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The API is reached through this proxy, so the browser sees a single origin.
// Deliberate: the backend then needs no CORS middleware, which means there is no
// permissive allow_origins setting sitting in the repo. See the spec, "Frontend".
//
// Port 8010, not 8000: an unrelated local service already occupies 8000 on the
// development machine, and two listeners on one port produce non-deterministic
// routing.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8010",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test-setup.ts",
  },
});
