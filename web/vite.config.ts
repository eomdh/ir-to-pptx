import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      output: {
        // echarts 를 이름 있는 지연 청크로 묶어 빌드 산출물이 스스로 설명되게 한다.
        // (동적 import 라 초기 로딩엔 안 들어가고, 차트가 처음 그려질 때만 받는다.)
        manualChunks: { echarts: ["echarts"] },
      },
    },
    // echarts 는 원래 무겁다. 지연 청크라 초기 번들엔 없으므로 경고 상한만 올린다.
    chunkSizeWarningLimit: 1100,
  },
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
