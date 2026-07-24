import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // dev 에선 프론트(5173)와 백엔드(8000)가 따로 뜬다.
    // /ir 호출만 백엔드로 넘겨 CORS 없이 같은 오리진처럼 쓴다.
    proxy: {
      "/ir": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
