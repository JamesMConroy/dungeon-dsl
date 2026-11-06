import { defineConfig } from "vitest/config";

// Separate from vite.config.ts: unit tests don't want the site's base or worker
// settings, and the default include would also pick up Playwright's e2e specs.
export default defineConfig({
  test: { include: ["src/**/*.test.ts"] },
});
