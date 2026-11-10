import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const screenshots = "artifacts/screens";

test.beforeEach(async ({page}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", {name: /Evidence, made visible/i})).toBeVisible();
  await expect(page.getByText("Validating public source artifacts…")).toHaveCount(0);
});

test("eight sections are reachable and real DEV metrics are visible", async ({page}) => {
  const titles = [
    ["MICRO-RAG v0.2","A system that knows when not to answer."],
    ["Experiments","Trade-offs, not just wins."],
    ["Pipeline","Every stage has a boundary."],
    ["Knowledge graph","Trace the source of every edge."],
    ["Evidence review","A citation is not a fact."],
    ["Model lab","Proposals are not measured results."],
    ["Methodology","Every result has a trail."],
    ["Overview","Evidence, made visible."],
  ];
  for (const [label,heading] of titles) {
    await page.getByRole("navigation",{name:"Research sections"}).getByRole("button",{name:label}).click();
    await expect(page.getByRole("heading",{name:heading})).toBeVisible();
  }
  await page.getByRole("navigation",{name:"Research sections"}).getByRole("button",{name:"Experiments"}).click();
  await expect(page.getByText("GRF-00 · Graph-first vs BM25")).toBeVisible();
  await expect(page.getByText("GRF-01 · Graph-Hybrid vs Hybrid RRF")).toBeVisible();
  await expect(page.getByText("−11.67 pp")).toHaveCount(0); // signed formatting is normal ASCII minus
  await expect(page.getByText("-11.67 pp")).toBeVisible();
});

test("graph and evidence inspector retain exact source quotations", async ({page}) => {
  await page.getByRole("navigation",{name:"Research sections"}).getByRole("button",{name:"Knowledge graph"}).click();
  const edge = page.getByRole("button",{name:/Orion Navigation System.*Meridian Robotics/i});
  await edge.click();
  await expect(page.getByText("The Orion Navigation System was developed by Meridian Robotics.")).toBeVisible();
  await page.getByRole("navigation",{name:"Research sections"}).getByRole("button",{name:"Evidence review"}).click();
  await page.getByRole("button",{name:/Engineering notes/}).click();
  await expect(page.getByRole("blockquote")).toHaveCount(1); // original source paragraph, not generated text
});

test("fixture truth claims stay disabled and models remain proposals", async ({page}) => {
  await page.getByRole("navigation",{name:"Research sections"}).getByRole("button",{name:"Pipeline"}).click();
  await expect(page.getByText("The static fixture invokes no language model")).toBeVisible();
  await page.getByRole("navigation",{name:"Research sections"}).getByRole("button",{name:"Model lab"}).click();
  await expect(page.getByText("Registry status: proposed.")).toBeVisible();
  await expect(page.getByText("Qwen/Qwen2.5-3B-Instruct")).toBeVisible();
});

test("theme toggle, keyboard navigation and narrow layout work", async ({page}) => {
  await page.getByRole("button",{name:"Use light theme"}).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme","light");
  await page.setViewportSize({width:390,height:844});
  await expect(page.getByRole("navigation",{name:"Research sections"})).toBeVisible();
  await page.getByRole("navigation",{name:"Research sections"}).getByRole("button",{name:"Experiments"}).click();
  await expect(page.getByRole("heading",{name:"Trade-offs, not just wins."})).toBeVisible();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth > window.innerWidth+4);
  expect(overflow).toBeFalsy();
});

test("screenshots for the public technical walkthrough", async ({page}) => {
  await mkdir(screenshots,{recursive:true});
  await page.screenshot({path:screenshots+"/01-overview.png",fullPage:true});
  await page.getByRole("navigation",{name:"Research sections"}).getByRole("button",{name:"Experiments"}).click();
  await page.screenshot({path:screenshots+"/02-experiments.png",fullPage:true});
  await page.getByRole("navigation",{name:"Research sections"}).getByRole("button",{name:"Knowledge graph"}).click();
  await page.screenshot({path:screenshots+"/03-graph.png",fullPage:true});
});

test("MICRO v0.2 replay verifies four outcomes and source offsets", async ({page}) => {
  await page.getByRole("navigation",{name:"Research sections"}).getByRole("button",{name:"MICRO-RAG v0.2"}).click();
  await expect(page.getByRole("heading",{name:"A system that knows when not to answer."})).toBeVisible();
  await expect(page.getByText("Verifying original document SHA256 and citations…")).toHaveCount(0);
  const picker=page.getByRole("region",{name:"Select an executed RAG scenario"});
  await expect(picker.getByRole("button")).toHaveCount(4);
  const result=page.getByRole("region",{name:"Micro RAG decision"});
  const citations=page.getByRole("region",{name:"Original cited sources"});
  await expect(result.getByText("No answer published.")).toBeVisible();
  await expect(citations.getByText("2012")).toBeVisible();
  await expect(citations.getByText("2015")).toBeVisible();
  await picker.getByRole("button",{name:/Compatible records/}).click();
  await expect(result.getByText("Verified literal value:")).toBeVisible();
  await expect(result.getByText("2019")).toBeVisible();
  await picker.getByRole("button",{name:/Missing information/}).click();
  await expect(result.getByText("No answer published.")).toBeVisible();
  await expect(citations.getByText("No cited value was found")).toBeVisible();
  await picker.getByRole("button",{name:/Incomplete evidence sweep/}).click();
  await expect(result.getByText("No answer published.")).toBeVisible();
  await expect(result.getByText("Full entity scan:")).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth > innerWidth + 4)).toBeFalsy();
});
