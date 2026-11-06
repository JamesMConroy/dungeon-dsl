import { defineConfig } from "@playwright/test";

// Runs against the built Playground, so `just web-build` must have run first.
const port = process.env.PW_PORT ?? "4173";

export default defineConfig({
  testDir: "e2e",
  forbidOnly: !!process.env.CI,
  // First load fetches Pyodide from jsDelivr.
  timeout: 60_000,
  expect: { timeout: 30_000 },
  use: { baseURL: `http://localhost:${port}/dungeon-dsl/` },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    command: `npm run preview -- --port ${port} --strictPort`,
    url: `http://localhost:${port}/dungeon-dsl/`,
    reuseExistingServer: !process.env.CI,
  },
});
