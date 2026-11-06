import { expect, test, type Page } from "@playwright/test";

const dungeonMap = (page: Page) => page.getByTestId("dungeon-map").locator("svg");

/** Appends text inside the quoted name on the editor line that holds it. */
async function extendRoomName(page: Page, name: string, suffix: string) {
  await page.locator(".cm-line", { hasText: `name: "${name}"` }).click();
  await page.keyboard.press("End");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.type(suffix);
}

test("renders goblin_warren and re-renders as the DM types", async ({ page }) => {
  await page.goto("./");

  await expect(dungeonMap(page).locator(".room")).toHaveCount(5);
  await expect(dungeonMap(page)).toContainText("Grand Hall");

  await extendRoomName(page, "Grand Hall", " Annex");

  await expect(dungeonMap(page)).toContainText("Grand Hall Annex");
});

test("the editor is usable while Python loads", async ({ page }) => {
  // Hold Pyodide's runtime back so the loading state can't race the assertions.
  let releaseRuntime = () => {};
  const runtimeHeld = new Promise<void>((resolve) => (releaseRuntime = resolve));
  await page.route("https://cdn.jsdelivr.net/**", async (route) => {
    await runtimeHeld;
    await route.continue();
  });

  await page.goto("./");
  await expect(page.getByTestId("map-pane")).toHaveAttribute("data-state", "loading");

  await extendRoomName(page, "Grand Hall", " Annex");
  releaseRuntime();

  await expect(dungeonMap(page)).toContainText("Grand Hall Annex");
});
