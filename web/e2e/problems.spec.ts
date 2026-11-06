import { expect, test, type Page } from "@playwright/test";

const mapPane = (page: Page) => page.getByTestId("map-pane");
const dungeonMap = (page: Page) => page.getByTestId("dungeon-map");
const errors = (page: Page) => page.locator(".cm-lintRange-error");
const problems = (page: Page) => page.getByTestId("problem");

/** Replaces the value after `key: ` on the first editor line holding `key: old`. */
async function replaceValue(page: Page, key: string, old: string, replacement: string) {
  await page.locator(".cm-line", { hasText: `${key}: ${old}` }).first().click();
  await page.keyboard.press("End");
  for (const _ of old) await page.keyboard.press("Backspace");
  await page.keyboard.type(replacement);
}

async function waitForFirstMap(page: Page) {
  await page.goto("./");
  await expect(dungeonMap(page).locator("svg")).toContainText("Grand Hall");
}

test("breaking a field shows an Error on that line over the greyed last good map, and fixing it recovers", async ({
  page,
}) => {
  await waitForFirstMap(page);

  await replaceValue(page, "size", "large", "huge");

  await expect(errors(page)).toHaveText("huge");
  await expect(page.locator(".cm-line", { hasText: "size: huge" }).locator(".cm-lintRange-error")).toBeVisible();
  await expect(problems(page)).toHaveCount(1);
  await expect(problems(page)).toHaveAttribute("data-severity", "error");
  await expect(problems(page)).toHaveAttribute("data-code", "pydantic.literal_error");

  await expect(mapPane(page)).toHaveAttribute("data-state", "invalid");
  await expect(page.getByTestId("map-banner")).toBeVisible();
  await expect(dungeonMap(page).locator("svg")).toContainText("Grand Hall");
  await expect(dungeonMap(page)).toHaveCSS("filter", "grayscale(1)");

  await replaceValue(page, "size", "huge", "large");

  await expect(mapPane(page)).toHaveAttribute("data-state", "ready");
  await expect(errors(page)).toHaveCount(0);
  await expect(problems(page)).toHaveCount(0);
  await expect(page.getByTestId("map-banner")).toBeHidden();
  await expect(dungeonMap(page)).toHaveCSS("filter", "none");
});

test("the room card stays on the last good Dungeon while the Dungeon is invalid", async ({ page }) => {
  await waitForFirstMap(page);
  const card = page.getByTestId("room-card");
  const room = (id: string) => dungeonMap(page).locator(`.room[data-room-id="${id}"]`);

  await room("entrance").click();
  await expect(card).toContainText("Grand Hall");

  await replaceValue(page, "size", "large", "huge");
  await expect(mapPane(page)).toHaveAttribute("data-state", "invalid");

  await expect(card).toContainText("Grand Hall");
  await expect(room("entrance")).toHaveClass(/selected/);

  await room("throne_room").click();
  await expect(card).toContainText("Goblin Throne");
});

test("clicking a Problem jumps to its line", async ({ page }) => {
  await waitForFirstMap(page);
  await replaceValue(page, "size", "large", "huge");
  await expect(problems(page)).toHaveCount(1);

  await page.locator(".cm-line", { hasText: 'name: "Goblin Warren"' }).click();
  await expect(page.locator(".cm-activeLine")).toContainText("Goblin Warren");

  await problems(page).click();

  await expect(page.locator(".cm-activeLine")).toContainText("size: huge");
  await expect(page.locator(".cm-editor")).toHaveClass(/cm-focused/);
});

test("a YAML syntax error is underlined and listed too", async ({ page }) => {
  await waitForFirstMap(page);

  await replaceValue(page, "size", "large", "a: b");

  await expect(problems(page)).toHaveAttribute("data-code", "yaml.syntax");
  await expect(mapPane(page)).toHaveAttribute("data-state", "invalid");
  await expect(errors(page)).toHaveCount(1);
});

test("underlines land on the right characters after an emoji", async ({ page }) => {
  await waitForFirstMap(page);

  await page.locator(".cm-content").click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.insertText(`{name: x, rooms: [{id: a, name: "🐉🐉", entrance: true, size: huge}]}`);

  await expect(errors(page)).toHaveText("huge");
});
