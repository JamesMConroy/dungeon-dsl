import { expect, test, type Locator, type Page } from "@playwright/test";

const map = (page: Page) => page.getByTestId("dungeon-map");
const room = (page: Page, id: string) => map(page).locator(`.room[data-room-id="${id}"]`);
const card = (page: Page) => page.getByTestId("room-card");
const cardTitle = (page: Page) => card(page).getByRole("heading", { level: 2 });

async function box(locator: Locator) {
  const found = await locator.boundingBox();
  if (!found) throw new Error("not on screen");
  return found;
}

const center = (b: { x: number; y: number; width: number; height: number }) => ({
  x: b.x + b.width / 2,
  y: b.y + b.height / 2,
});

async function drag(page: Page, from: { x: number; y: number }, by: { x: number; y: number }) {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(from.x + by.x / 2, from.y + by.y / 2);
  await page.mouse.move(from.x + by.x, from.y + by.y);
  await page.mouse.up();
}

async function replaceYaml(page: Page, text: string) {
  await page.locator(".cm-content").click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.insertText(text);
}

const TWO_ROOMS = `name: Small
rooms:
  - id: hall
    name: Hall
    entrance: true
    exits:
      - { target: pit, direction: e }
  - id: pit
    name: Pit
`;

const THREE_ROOMS = `${TWO_ROOMS}    exits:
      - { target: vault, direction: e }
  - id: vault
    name: Vault
`;

test.beforeEach(async ({ page }) => {
  await page.goto("./");
  await expect(map(page).locator(".room")).toHaveCount(5);
});

test("dragging the map moves it with the pointer", async ({ page }) => {
  const before = await box(room(page, "entrance"));

  await drag(page, center(await box(room(page, "throne_room"))), { x: 40, y: 25 });

  const after = await box(room(page, "entrance"));
  expect(after.x - before.x).toBeCloseTo(40, 0);
  expect(after.y - before.y).toBeCloseTo(25, 0);
});

test("a drag that ends on a Room doesn't open its card, but a click still does", async ({ page }) => {
  await drag(page, center(await box(room(page, "entrance"))), { x: 30, y: 0 });
  await expect(cardTitle(page)).toHaveCount(0);

  await room(page, "entrance").click();
  await expect(cardTitle(page)).toContainText("Grand Hall");
});

test("the wheel zooms around the pointer", async ({ page }) => {
  const before = await box(room(page, "entrance"));
  const pointer = center(before);

  await page.mouse.move(pointer.x, pointer.y);
  await page.mouse.wheel(0, -200);
  await expect.poll(async () => (await box(room(page, "entrance"))).width).toBeGreaterThan(before.width * 1.2);

  const after = center(await box(room(page, "entrance")));
  expect(after.x).toBeCloseTo(pointer.x, 0);
  expect(after.y).toBeCloseTo(pointer.y, 0);
});

test("the buttons zoom in, zoom out and fit", async ({ page }) => {
  const fitted = await box(room(page, "entrance"));

  await page.getByRole("button", { name: "Zoom in" }).click();
  expect((await box(room(page, "entrance"))).width).toBeGreaterThan(fitted.width);

  await page.getByRole("button", { name: "Zoom out" }).click();
  await page.getByRole("button", { name: "Zoom out" }).click();
  expect((await box(room(page, "entrance"))).width).toBeLessThan(fitted.width);

  await page.getByRole("button", { name: "Fit map" }).click();
  expect(await box(room(page, "entrance"))).toEqual(fitted);
});

test("editing a description keeps the view", async ({ page }) => {
  await room(page, "entrance").click();
  await page.getByRole("button", { name: "Zoom in" }).click();
  await drag(page, center(await box(room(page, "entrance"))), { x: 20, y: 20 });
  const view = await box(room(page, "entrance"));

  await page.locator(".cm-line", { hasText: "A cavernous chamber" }).click();
  await page.keyboard.press("End");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.type(" Rats.");

  await expect(card(page)).toContainText("Rats.");
  expect(await box(room(page, "entrance"))).toEqual(view);
});

test("adding a Room that grows the bounds refits", async ({ page }) => {
  await replaceYaml(page, TWO_ROOMS);
  await expect(map(page).locator(".room")).toHaveCount(2);
  await page.getByRole("button", { name: "Zoom in" }).click();

  await replaceYaml(page, THREE_ROOMS);
  await expect(map(page).locator(".room")).toHaveCount(3);

  const shown = await box(room(page, "hall"));
  await page.getByRole("button", { name: "Fit map" }).click();
  expect(await box(room(page, "hall"))).toEqual(shown);
});

test.describe("on a touch screen", () => {
  test.use({ hasTouch: true });

  type Touch = { x: number; y: number };

  async function touchscreen(page: Page) {
    const session = await page.context().newCDPSession(page);
    return (type: "touchStart" | "touchMove" | "touchEnd", touchPoints: Touch[]) =>
      session.send("Input.dispatchTouchEvent", { type, touchPoints });
  }

  test("one finger pans", async ({ page }) => {
    const before = await box(room(page, "entrance"));
    const start = center(before);
    const touch = await touchscreen(page);

    await touch("touchStart", [start]);
    await touch("touchMove", [{ x: start.x + 20, y: start.y + 10 }]);
    await touch("touchMove", [{ x: start.x + 40, y: start.y + 25 }]);
    await touch("touchEnd", []);

    const after = await box(room(page, "entrance"));
    expect(after.x - before.x).toBeCloseTo(40, 0);
    expect(after.y - before.y).toBeCloseTo(25, 0);
  });

  test("two fingers pinch to zoom", async ({ page }) => {
    const before = await box(room(page, "entrance"));
    const { x, y } = center(before);
    const touch = await touchscreen(page);

    await touch("touchStart", [
      { x: x - 20, y },
      { x: x + 20, y },
    ]);
    await touch("touchMove", [
      { x: x - 40, y },
      { x: x + 40, y },
    ]);
    await touch("touchEnd", []);

    const after = await box(room(page, "entrance"));
    expect(after.width).toBeCloseTo(before.width * 2, 0);
    expect(center(after).x).toBeCloseTo(x, 0);
  });

  test("a tap on a Room still shows its card", async ({ page }) => {
    const { x, y } = center(await box(room(page, "entrance")));

    await page.touchscreen.tap(x, y);

    await expect(cardTitle(page)).toContainText("Grand Hall");
  });
});
