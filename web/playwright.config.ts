import { defineConfig } from "@playwright/test";

// Runs against the built site, so `just web-build` must have run first.
export default defineConfig({
  testDir: "e2e",
  forbidOnly: !!process.env.CI,
  // First load fetches Pyodide from jsDelivr.
  timeout: 60_000,
  expect: { timeout: 30_000 },
  use: { baseURL: "http://localhost:4173/dungeon-dsl/" },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    command: "npm run preview -- --port 4173 --strictPort",
    url: "http://localhost:4173/dungeon-dsl/",
    reuseExistingServer: !process.env.CI,
  },
});
