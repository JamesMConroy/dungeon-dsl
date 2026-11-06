import { defineConfig } from "vite";

export default defineConfig({
  base: "/dungeon-dsl/",
  // Pyodide's worker needs ES output; classic workers can't load it.
  worker: { format: "es" },
  // Pyodide resolves its own assets at runtime; pre-bundling breaks that in dev.
  optimizeDeps: { exclude: ["pyodide"] },
  // The bundled examples live at the repo root, outside the Vite root.
  server: { fs: { allow: [".."] } },
});
