import { defineConfig } from "vite";

export default defineConfig({
  base: "/lab/",
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/lab/api": {
        target: "http://127.0.0.1:8090",
        changeOrigin: false,
      },
      "/v1": {
        target: "http://127.0.0.1:8090",
        changeOrigin: false,
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
  },
});
