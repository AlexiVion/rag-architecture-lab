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
  await page.getByRole("navigation", { name: "Research sections" }).getByRole("button", { name: "Research" }).click();
  for (let i=0;i<3;i++) await page.getByRole("button", { name: "Step", exact: true }).click();
  await page.waitForTimeout(650);
  await page.screenshot({ path: "artifacts/screens/05-playground-ranking.png", fullPage: true });
});


test("Architecture Playground compares two distinct methods and advances through real RRF logic", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Architecture Playground" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Educational architecture comparison" })).toBeVisible();
  const left = page.getByLabel("Left architecture");
  const right = page.getByLabel("Right architecture");
  await expect(left).toHaveValue("bm25");
  await expect(right).toHaveValue("hybrid");
  await right.selectOption("rerank");
  await expect(right).toHaveValue("rerank");
  await page.getByRole("button", { name: "Step", exact: true }).click();
  await expect(page.getByText("Stage 2 of 5")).toBeVisible();
  await page.getByRole("button", { name: "Step", exact: true }).click();
  await expect(page.getByText("Stage 3 of 5")).toBeVisible();
  await expect(page.getByRole("region", { name: "Right ranking" }).getByRole("listitem", {name: /Rank 1: Plant roots/})).toBeVisible();
  await page.getByRole("button", { name: "Step", exact: true }).click();
  await expect(page.getByText("Stage 4 of 5")).toBeVisible();
  await page.getByRole("button", { name: "Step", exact: true }).click();
  await expect(page.getByText("Stage 5 of 5")).toBeVisible();
  // Wait for the positional transition and verify the final stacked ranking is not overlapping.
  await page.waitForTimeout(650);
  const topPositions=await page.getByRole("region", { name: "Right ranking" }).locator(".ap-rank-card").evaluateAll(cards =>
    cards.map(card => Math.round(card.getBoundingClientRect().top)));
  expect(new Set(topPositions).size).toBe(5);
  await expect(page.getByText(/Illustrative rankings, not SciFact outputs/)).toBeVisible();
  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await expect(page.getByText("Stage 1 of 5")).toBeVisible();
  // Selecting the same architecture swaps the other lane rather than comparing an algorithm to itself.
  await left.selectOption("rerank");
  await expect(left).toHaveValue("rerank");
  await expect(right).not.toHaveValue("rerank");
});

test("Play/Pause and scenario changes update architecture comparison without live inference", async ({ page }) => {
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await expect(page.getByRole("button", { name: "Pause", exact: true })).toBeVisible();
  await expect(page.getByText("Stage 2 of 5")).toBeVisible({ timeout: 6000 });
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await expect(page.getByRole("button", { name: "Play", exact: true })).toBeVisible();
  await page.getByLabel("Teaching question").selectOption("penguins");
  await expect(page.getByText("Stage 1 of 5")).toBeVisible();
  await expect(page.locator(".ap-selected-question strong")).toHaveText("Can penguins fly?");
  await expect(page.getByText(/fictional teaching documents/i).first()).toBeVisible();
});

test("Simple, technical and scientific explanations never promote illustrative data to measured results", async ({ page }) => {
  await page.getByRole("radio", { name: "Simple" }).check();
  await expect(page.getByText(/two ways to look for useful clues/i)).toBeVisible();
  await page.getByRole("radio", { name: "Technical" }).check();
  await expect(page.getByText(/reciprocal rank fusion/i)).toBeVisible();
  await page.getByRole("radio", { name: "Scientific" }).check();
  await expect(page.getByText(/not empirical per-query SciFact measurements/i)).toBeVisible();
});

test("quality and query latency are scoped to one measurement environment", async ({ page }) => {
  await page.getByLabel("Recorded study").selectOption("v0");
  await expect(page.locator(".ap-study-points").getByText("7.52 ms", {exact:true})).toBeVisible();
  await expect(page.locator(".ap-study-points").getByText("51.86 ms", {exact:true})).toBeVisible();
  await expect(page.getByText("GitHub Actions · Ubuntu 24.04 · same V0 run")).toBeVisible();
  await page.locator(".ap-study-points").getByRole("button", { name: /Dense/ }).click();
  await expect(page.getByText(/Selected: Dense/)).toBeVisible();
  await page.getByLabel("Recorded study").selectOption("v1");
  await expect(page.locator(".ap-study-points").getByText("34.53 ms", {exact:true})).toBeVisible();
  await expect(page.locator(".ap-study-points").getByText("3,706.43 ms", {exact:true})).toBeVisible();
  await expect(page.getByText("Windows 11 · AMD Ryzen 7 5700U · same V1 run")).toBeVisible();
  await expect(page.locator(".ap-study-points").getByText("7.52 ms", {exact:true})).toHaveCount(0);
});

test("the comparison remains usable at mobile width and in dark mode", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByLabel("Teaching question").selectOption("moon");
  await page.getByRole("button", { name: "Step", exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 3)).toBeFalsy();
  await mkdir("artifacts/screens", { recursive: true });
  await page.screenshot({ path: "artifacts/screens/04-playground-mobile.png", fullPage: true });
});


test("Document X-Ray inspects the selected card with exact RRF arithmetic and follows timeline", async ({page})=>{
  await page.getByRole("button",{name:"Step",exact:true}).click();
  const left=page.getByRole("region",{name:"Left ranking"});
  const right=page.getByRole("region",{name:"Right ranking"});
  await left.getByRole("button",{name:/Inspect Plant roots/}).click();
  const inspector=page.getByRole("region",{name:"Document X-Ray"});
  await expect(inspector.getByRole("heading",{name:"Plant roots"})).toBeVisible();
  await expect(inspector.getByText("BM25",{exact:true})).toBeVisible();
  await expect(inspector.getByText("Dense",{exact:true})).toBeVisible();
  await expect(inspector.getByText("Hybrid RRF",{exact:true})).toBeVisible();
  await expect(inspector.getByText("Scripted reranking",{exact:true})).toBeVisible();
  await expect(inspector.getByText(/1 \/ \(60 \+ 2\)/)).toBeVisible();
  await expect(inspector.getByText(/1 \/ \(60 \+ 1\)/)).toBeVisible();
  await expect(inspector.getByText(/Author-created ranks are not SciFact measurements/)).toBeVisible();
  await expect(inspector.getByText(/Left: #2/)).toBeVisible();
  await expect(inspector.getByText(/Right: #2/)).toBeVisible();
  await page.getByRole("button",{name:"Step",exact:true}).click();
  await expect(inspector.getByText(/Left: #2/)).toBeVisible();
  await expect(inspector.getByText(/Right: #1/)).toBeVisible();
  await mkdir("artifacts/screens",{recursive:true});
  await inspector.screenshot({path:"artifacts/screens/06-document-xray-desktop.png"});
  await expect(left.getByRole("button",{name:/Inspect Plant roots/})).toHaveAttribute("aria-pressed","true");
  await expect(right.getByRole("button",{name:/Inspect Plant roots/})).toHaveAttribute("aria-pressed","true");
  await inspector.getByRole("button",{name:"Close inspection"}).click();
  await expect(inspector).toHaveCount(0);
});

test("Document X-Ray respects explanation mode, reset and question switching",async ({page})=>{
  await page.getByRole("button",{name:"Step",exact:true}).click();
  await page.getByRole("region",{name:"Right ranking"}).getByRole("button",{name:/Inspect Rain gardens/}).focus();
  await page.keyboard.press("Enter");
  const inspector=page.getByRole("region",{name:"Document X-Ray"});
  await expect(inspector.getByRole("heading",{name:"Rain gardens"})).toBeVisible();
  await page.getByRole("radio",{name:"Technical"}).check();
  await expect(inspector.getByText(/RRF combines two position-based terms/)).toBeVisible();
  await page.getByRole("radio",{name:"Scientific"}).check();
  await expect(inspector.getByText(/No BM25 term weights, embedding similarity or cross-encoder scores were measured/)).toBeVisible();
  await page.getByLabel("Teaching question").selectOption("penguins");
  await expect(inspector).toHaveCount(0);
  await page.getByRole("button",{name:"Step",exact:true}).click();
  await page.getByRole("region",{name:"Left ranking"}).getByRole("button",{name:/Inspect Penguin movement/}).click();
  await expect(inspector).toBeVisible();
  await page.getByRole("button",{name:"Reset",exact:true}).click();
  await expect(inspector).toHaveCount(0);
});
test("Document X-Ray remains usable on a narrow dark-mode viewport",async ({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.getByRole("button",{name:"Use dark theme"}).click();
  await page.getByRole("button",{name:"Step",exact:true}).click();
  await page.getByRole("region",{name:"Left ranking"}).getByRole("button",{name:/Inspect Plant roots/}).click();
  await expect(page.getByRole("region",{name:"Document X-Ray"})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+3)).toBe(false);
  await mkdir("artifacts/screens",{recursive:true});
  await page.getByRole("region",{name:"Document X-Ray"}).screenshot({path:"artifacts/screens/07-document-xray-mobile.png"});
});
