import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test, type Page } from "@playwright/test";

const examplesDir = join(import.meta.dirname, "..", "..", "examples");
const exampleNames = readdirSync(examplesDir)
  .filter((file) => file.endsWith(".yaml"))
  .map((file) => file.replace(/\.yaml$/, ""));
const exampleText = (name: string) => readFileSync(join(examplesDir, `${name}.yaml`), "utf8");
/** The Dungeon's name, as the map's title draws it. */
const dungeonName = (name: string) => exampleText(name).match(/^name: "(.+)"$/m)![1];

const dungeonMap = (page: Page) => page.getByTestId("dungeon-map").locator("svg");
const examplePicker = (page: Page) => page.getByRole("combobox", { name: "Load example" });

/** Appends text inside the quoted name of the Grand Hall's editor line. */
async function extendGrandHall(page: Page, suffix: string) {
  await page.locator(".cm-line", { hasText: 'name: "Grand Hall"' }).click();
  await page.keyboard.press("End");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.type(suffix);
}

async function replaceDocument(page: Page, text: string) {
  await page.locator(".cm-content").click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.type(text);
}

async function downloadText(page: Page, button: string) {
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: button }).click()]);
  return { name: download.suggestedFilename(), text: readFileSync(await download.path(), "utf8") };
}

test("the dropdown lists every bundled example and loads the chosen one", async ({ page }) => {
  await page.goto("./");
  await expect(dungeonMap(page)).toContainText(dungeonName("goblin_warren"));

  const listed = await examplePicker(page).getByRole("option", { disabled: false }).allTextContents();
  expect(listed.sort()).toEqual([...exampleNames].sort());

  for (const name of exampleNames.filter((name) => name !== "goblin_warren")) {
    await examplePicker(page).selectOption(name);
    await expect(dungeonMap(page)).toContainText(dungeonName(name));
    await expect(page.locator(".cm-content")).toContainText(dungeonName(name));
  }
});

test("an example can be reloaded to throw away edits", async ({ page }) => {
  await page.goto("./");
  await expect(dungeonMap(page)).toContainText("Grand Hall");

  await extendGrandHall(page, " Annex");
  await expect(dungeonMap(page)).toContainText("Grand Hall Annex");

  await examplePicker(page).selectOption("goblin_warren");

  await expect(dungeonMap(page)).not.toContainText("Grand Hall Annex");
  await expect(page.locator(".cm-content")).not.toContainText("Grand Hall Annex");
});

test("loading an example clears a Permalink from the URL", async ({ page }) => {
  await page.goto("./#1.not-a-real-dungeon");
  await expect(page).toHaveURL(/#/);

  await examplePicker(page).selectOption("size_test");

  await expect(dungeonMap(page)).toContainText(dungeonName("size_test"));
  await expect(page).not.toHaveURL(/#/);
});

test("Download YAML saves the editor contents, valid or not", async ({ page }) => {
  await page.goto("./");
  await expect(dungeonMap(page)).toContainText("Grand Hall");

  await extendGrandHall(page, " Annex");
  const edited = await downloadText(page, "Download YAML");
  expect(edited.name).toMatch(/\.yaml$/);
  expect(edited.text).toBe(exampleText("goblin_warren").replace('"Grand Hall"', '"Grand Hall Annex"'));

  await replaceDocument(page, "not a dungeon");
  expect((await downloadText(page, "Download YAML")).text).toBe("not a dungeon");
});

test("Download SVG saves the last good map, even while the YAML is invalid", async ({ page }) => {
  await page.goto("./");
  await expect(dungeonMap(page)).toContainText("Grand Hall");

  await extendGrandHall(page, " Annex");
  await expect(dungeonMap(page)).toContainText("Grand Hall Annex");
  await replaceDocument(page, "not a dungeon");
  await expect(page.getByTestId("map-pane")).not.toHaveAttribute("data-state", "ready");

  const { name, text } = await downloadText(page, "Download SVG");

  expect(name).toMatch(/\.svg$/);
  // A standalone file, not a fragment of the page.
  expect(text).toMatch(/^(<\?xml[^>]*>\s*)?<svg\b[^>]*\bxmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
  expect(text).toContain("Grand Hall Annex");
});

test("Download SVG waits for there to be a map", async ({ page }) => {
  let releaseRuntime = () => {};
  const runtimeHeld = new Promise<void>((resolve) => (releaseRuntime = resolve));
  await page.route("https://cdn.jsdelivr.net/**", async (route) => {
    await runtimeHeld;
    await route.continue();
  });

  await page.goto("./");
  await expect(page.getByRole("button", { name: "Download SVG" })).toBeDisabled();

  releaseRuntime();

  await expect(page.getByRole("button", { name: "Download SVG" })).toBeEnabled();
});
