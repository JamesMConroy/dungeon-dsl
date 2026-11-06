import { expect, test, type Locator, type Page } from "@playwright/test";

const WIDE = { width: 1280, height: 720 };
const NARROW = { width: 390, height: 700 };
const WHITE = "rgb(255, 255, 255)";

const map = (page: Page) => page.getByTestId("dungeon-map");
const room = (page: Page, id: string) => map(page).locator(`.room[data-room-id="${id}"]`);
const card = (page: Page) => page.getByTestId("room-card");
const cardTitle = (page: Page) => card(page).getByRole("heading", { level: 2 });
const editor = (page: Page) => page.locator(".cm-content");
const drawerButton = (page: Page) => page.getByRole("button", { name: "Edit YAML" });
const closeDrawer = (page: Page) => page.getByRole("button", { name: "Close YAML" });
const badge = (page: Page) => page.getByTestId("problem-count");

async function box(locator: Locator) {
  const found = await locator.boundingBox();
  if (!found) throw new Error("not on screen");
  return found;
}

/** How far apart two boxes are; 0 if they touch or overlap. */
function gapBetween(a: { x: number; y: number; width: number; height: number }, b: typeof a) {
  const across = Math.max(a.x - (b.x + b.width), b.x - (a.x + a.width));
  const down = Math.max(a.y - (b.y + b.height), b.y - (a.y + a.height));
  return Math.max(0, across, down);
}

async function expectPopoverBy(page: Page, id: string) {
  const popover = await box(card(page));
  expect(gapBetween(popover, await box(room(page, id)))).toBeLessThanOrEqual(16);
  expect(popover.x).toBeGreaterThanOrEqual(0);
  expect(popover.y).toBeGreaterThanOrEqual(0);
  const { width, height } = page.viewportSize()!;
  expect(popover.x + popover.width).toBeLessThanOrEqual(width);
  expect(popover.y + popover.height).toBeLessThanOrEqual(height);
}

async function replaceYaml(page: Page, text: string) {
  await editor(page).click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.insertText(text);
}

const TWO_PROBLEMS = `name: Broken
rooms:
  - id: hall
    name: Hall
    size: wrong
    light: wrong
`;

const VALID = `name: Fine
rooms:
  - id: hall
    name: Hall
    entrance: true
`;

async function openPlayground(page: Page, viewport: { width: number; height: number }) {
  await page.setViewportSize(viewport);
  await page.goto("./");
  await expect(map(page).locator(".room")).toHaveCount(5);
}

test("wide screens get the Workbench: every pane on show, no drawer", async ({ page }) => {
  await openPlayground(page, WIDE);

  await expect(editor(page)).toBeVisible();
  await expect(card(page)).toBeVisible();
  await expect(drawerButton(page)).toBeHidden();
});

test("narrow screens get Map-first: the map fills the screen", async ({ page }) => {
  await openPlayground(page, NARROW);

  await expect(editor(page)).toBeHidden();
  await expect(card(page)).toBeHidden();
  await expect(drawerButton(page)).toBeVisible();

  const pane = await box(page.getByTestId("map-pane"));
  expect(pane.width).toBe(NARROW.width);
  expect(pane.y + pane.height).toBe(NARROW.height);
  expect(pane.height).toBeGreaterThan(NARROW.height * 0.7);
});

test("the YAML lives in a drawer that opens, edits the map, and closes", async ({ page }) => {
  await openPlayground(page, NARROW);

  await drawerButton(page).click();
  await expect(editor(page)).toBeVisible();

  await replaceYaml(page, VALID);
  await expect(map(page).locator(".room")).toHaveCount(1);

  await closeDrawer(page).click();
  await expect(editor(page)).toBeHidden();
});

test("the drawer badge shows the current Problem count", async ({ page }) => {
  await openPlayground(page, NARROW);
  await expect(badge(page)).toBeHidden();

  await drawerButton(page).click();
  await replaceYaml(page, TWO_PROBLEMS);
  await expect(page.getByTestId("problem")).toHaveCount(2);
  await expect(badge(page)).toHaveText("2");

  await replaceYaml(page, VALID);
  await expect(page.getByTestId("problem")).toHaveCount(0);
  await expect(badge(page)).toBeHidden();
});

test("the room card is a popover by the clicked Room", async ({ page }) => {
  await openPlayground(page, NARROW);

  await room(page, "throne_room").click();

  await expect(cardTitle(page)).toContainText("Goblin Throne");
  await expectPopoverBy(page, "throne_room");
});

test("an exit link moves the popover to the Room it names", async ({ page }) => {
  await openPlayground(page, NARROW);
  await room(page, "entrance").click();

  await card(page).getByRole("button", { name: "2. North Passage" }).click();

  await expect(cardTitle(page)).toContainText("North Passage");
  await expectPopoverBy(page, "corridor_north");
});

test("the popover follows its Room when the map pans", async ({ page }) => {
  await openPlayground(page, NARROW);
  await room(page, "entrance").click();
  const before = await box(card(page));

  // From a corner of the map, so the drag can't start under the popover.
  const pane = await box(page.getByTestId("map-pane"));
  await page.mouse.move(pane.x + 20, pane.y + pane.height - 20);
  await page.mouse.down();
  await page.mouse.move(pane.x + 20, pane.y + pane.height - 60);
  await page.mouse.up();

  await expect.poll(async () => (await box(card(page))).y).toBeLessThan(before.y);
  await expect(cardTitle(page)).toContainText("Grand Hall");
  await expectPopoverBy(page, "entrance");
});

test("the popover closes with its button or a click on the bare map", async ({ page }) => {
  await openPlayground(page, NARROW);

  await room(page, "entrance").click();
  await card(page).getByRole("button", { name: "Close room card" }).click();
  await expect(card(page)).toBeHidden();
  await expect(room(page, "entrance").locator("rect")).toHaveCSS("fill", WHITE);

  await room(page, "entrance").click();
  await expect(card(page)).toBeVisible();
  const pane = await box(page.getByTestId("map-pane"));
  await page.mouse.click(pane.x + 4, pane.y + pane.height - 4);
  await expect(card(page)).toBeHidden();
});

test("resizing across the breakpoint keeps the editor's text and the selected Room", async ({ page }) => {
  await openPlayground(page, WIDE);
  await room(page, "throne_room").click();
  await page.locator(".cm-line", { hasText: 'name: "Grand Hall"' }).click();
  await page.keyboard.press("End");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.type(" Annex");
  await expect(map(page)).toContainText("Grand Hall Annex");

  await page.setViewportSize(NARROW);

  await expect(drawerButton(page)).toBeVisible();
  await expect(cardTitle(page)).toContainText("Goblin Throne");
  await expect(room(page, "throne_room").locator("rect")).not.toHaveCSS("fill", WHITE);
  await expect.poll(async () => {
    await expectPopoverBy(page, "throne_room");
    return true;
  }).toBe(true);
  await drawerButton(page).click();
  await expect(editor(page)).toContainText("Grand Hall Annex");

  await page.setViewportSize(WIDE);

  await expect(drawerButton(page)).toBeHidden();
  await expect(editor(page)).toBeVisible();
  await expect(editor(page)).toContainText("Grand Hall Annex");
  await expect(cardTitle(page)).toContainText("Goblin Throne");
  await expect(room(page, "throne_room").locator("rect")).not.toHaveCSS("fill", WHITE);
});
