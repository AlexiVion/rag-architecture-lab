import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:4875",
    trace: "retain-on-failure",
  },
  projects: [
    {name: "chromium", use: {...devices["Desktop Chrome"]}}
  ],
  webServer: {
    command: "npm run preview -- --host 127.0.0.1 --port 4875",
    url: "http://127.0.0.1:4875/",
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
  reporter: [["list"]],
});
