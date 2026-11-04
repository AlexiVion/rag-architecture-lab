import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  build: { outDir: "dist", sourcemap: false, target: "es2022" },
  server: { host: "127.0.0.1", port: 4874, strictPort: true },
  preview: { host: "127.0.0.1", port: 4875, strictPort: true },
});
