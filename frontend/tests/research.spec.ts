import { test, expect } from "@playwright/test";

test("research explanations trap focus, close with Escape and restore the trigger", async ({ page }) => {
  await page.goto("/");
  const trigger = page.getByRole("button", { name: "Araştırmanın amacı", exact: true });
  await trigger.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Araştırma neyi inceliyor?" })).toBeVisible();
  await expect(dialog).toContainText("Kontrollü senaryo sonuçları");
  await expect(dialog.getByRole("button", { name: "Açıklamayı kapat" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(dialog.getByRole("button", { name: "Anladım, devam et" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await page.getByRole("button", { name: "Ev fazı nasıl kullanılır?", exact: true }).click();
  await expect(dialog).toContainText("HR03");
  await dialog.getByRole("button", { name: "Anladım, devam et" }).click();
  await expect(dialog).not.toBeVisible();
});

test("research tables and downloads reflect the recorded benchmark", async ({ page, request }) => {
  await page.goto("/");
  const table = page.getByRole("table");
  await expect(table.locator("tfoot")).toContainText("85");
  await expect(table.locator("tfoot")).toContainText("842");
  await page.getByRole("button", { name: "M04 formülü ve sınırları", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("min(1, P_etkin × t_uygun / E_gün)");
  await expect(page.getByRole("dialog")).toContainText("Bir ürün puanı veya saha başarı oranı değildir");
  await page.keyboard.press("Escape");
  const summary = await request.get("/research/benchmark-ozeti.json");
  expect(summary.ok()).toBe(true);
  expect((await summary.json()).total_alternatives).toBe(2153);
  for (const filename of ["veri-paketi.md", "deney-senaryolari.md", "entegrasyon.md"]) {
    const response = await request.get(`/research/${filename}`);
    expect(response.ok()).toBe(true);
    expect(await response.text()).toContain("# ");
  }
});

test("research dialogs and paper fit a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("button", { name: "Sistem mimarisini incele", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const bounds = await dialog.boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(390);
  expect(await dialog.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
});
