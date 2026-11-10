import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /How small can reliable RAG be/i })).toBeVisible();
});

test("editorial navigation contains only three main sections", async ({ page }) => {
  const nav = page.getByRole("navigation", { name: "Research sections" });
  await expect(nav.getByRole("button")).toHaveCount(3);
  await nav.getByRole("button", { name: "Experiments" }).click();
  await expect(page.getByRole("heading", { name: "What the experiments actually show." })).toBeVisible();
  await expect(page.getByText("BEIR SciFact · 5,183 documents · 300 queries")).toBeVisible();
  await expect(page.getByText("0.6484", { exact: true }).first()).toBeVisible();
  await nav.getByRole("button", { name: "Methodology" }).click();
  await expect(page.getByRole("heading", { name: "Results are useful only with their conditions." })).toBeVisible();
  await nav.getByRole("button", { name: "Research" }).click();
  await expect(page.getByRole("heading", { name: /How small can reliable RAG be/i })).toBeVisible();
});

test("verified Python replay changes evidence and decision, never claims live inference", async ({ page }) => {
  const group = page.getByRole("group", { name: "Choose an evidence scenario" });
  await expect(group.getByRole("button")).toHaveCount(4);
  const decision = page.getByRole("region", { name: "Recorded pipeline decision" });
  await expect(decision.getByText("CONFLICT")).toBeVisible();
  await expect(page.getByText("“2012”")).toBeVisible();
  await expect(page.getByText("“2015”")).toBeVisible();
  await expect(decision.getByText("No definitive answer published.")).toBeVisible();
  await group.getByRole("button", { name: /Compatible records/ }).click();
  await expect(decision.getByText("ANSWER")).toBeVisible();
  await expect(decision.getByText("Returned literal value:")).toBeVisible();
  await group.getByRole("button", { name: /Missing information/ }).click();
  await expect(decision.getByText("INSUFFICIENT")).toBeVisible();
  await group.getByRole("button", { name: /Incomplete evidence sweep/ }).click();
  await expect(decision.getByText("REVIEW", { exact: true })).toBeVisible();
  await expect(page.getByText(/Not live inference/)).toBeVisible();
});

test("technical provenance can be revealed without visual clutter", async ({ page }) => {
  await expect(page.getByText(/SHA256:/).first()).not.toBeVisible();
  await page.getByText("Verify source").first().click();
  await expect(page.getByText(/SHA256:/).first()).toBeVisible();
});

test("measured values and limitations are not hidden", async ({ page }) => {
  await page.getByRole("navigation", { name: "Research sections" }).getByRole("button", { name: "Experiments" }).click();
  await expect(page.getByText("0.6328", { exact: true })).toBeVisible();
  await expect(page.getByText("0.6484", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("3,706.43", { exact: false })).toBeVisible();
  await expect(page.getByText(/not a matched-training model comparison/i)).toBeVisible();
  await expect(page.getByText(/not independent questions/i)).toBeVisible();
});

test("theme and mobile layout do not overflow horizontally", async ({ page }) => {
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.setViewportSize({ width: 390, height: 844 });
  for (const name of ["Research", "Experiments", "Methodology"]) {
    await page.getByRole("navigation", { name: "Research sections" }).getByRole("button", { name }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 3)).toBeFalsy();
  }
});

test("record screenshots for editorial interface review", async ({ page }) => {
  await mkdir("artifacts/screens", { recursive: true });
  await page.screenshot({ path: "artifacts/screens/01-research.png", fullPage: true });
  await page.getByRole("navigation", { name: "Research sections" }).getByRole("button", { name: "Experiments" }).click();
  await page.screenshot({ path: "artifacts/screens/02-experiments.png", fullPage: true });
  await page.getByRole("navigation", { name: "Research sections" }).getByRole("button", { name: "Methodology" }).click();
  await page.screenshot({ path: "artifacts/screens/03-methodology.png", fullPage: true });
});
