import { test, expect, Page } from "@playwright/test";

async function confirmHome(page: Page, phase = "monofaz") {
  await page.goto("/");
  await page.getByLabel("Ev fazı").selectOption(phase);
  await expect(page.getByRole("button", { name: "Araç bilgilerine geç" })).toBeDisabled();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Araç bilgilerine geç" }).click();
  await expect(page.getByLabel("Katalogdan aracınızı seçin")).toBeEnabled();
  await page.getByLabel("Katalogdan aracınızı seçin").selectOption("EU_EVDB_3305_T10F_LONG_RANGE_RWD");
  await page.getByLabel("Günlük ortalama mesafe").fill("30");
  await page.getByLabel("Evde şarja uygun süre").fill("12");
}

test("real API: confirmation, candidate groups, explanation and export", async ({ page }) => {
  await confirmHome(page);
  await page.getByRole("button", { name: "Şarj adaylarını değerlendir" }).click();
  await expect(page.getByRole("heading", { name: "Şarj adaylarınız." })).toBeVisible();
  await expect(page.getByRole("tab", { name: /Değerlendirilebilir/ })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator(".candidate")).not.toHaveCount(0);
  await page.locator(".candidate").first().getByText("Gerekçeler ve tüm metrikler").click();
  await expect(page.locator(".candidate").first().getByText("HR08", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: /Teknik olarak elenen/ }).click();
  await expect(page.getByRole("heading", { name: "Wall Connector", exact: true })).toHaveCount(0);
  await expect(page.locator(".candidate .metric-grid")).toHaveCount(0);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Sonuçları indir" }).click();
  expect((await downloadPromise).suggestedFilename()).toBe("evcsds-sonuclar.json");
});

test("editing home invalidates confirmation and previous results", async ({ page }) => {
  await confirmHome(page);
  await page.getByRole("button", { name: "Şarj adaylarını değerlendir" }).click();
  await expect(page.getByRole("heading", { name: "Şarj adaylarınız." })).toBeVisible();
  await page.getByRole("button", { name: "Bilgileri düzenle", exact: true }).click();
  await page.getByLabel("Ev fazı").selectOption("trifaz");
  await expect(page.getByRole("checkbox")).not.toBeChecked();
  await expect(page.getByRole("button", { name: "Araç bilgilerine geç" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Aday sonuçları" })).toBeDisabled();
});

test("unknown phase does not invent eligible products", async ({ page }) => {
  await confirmHome(page, "belirsiz");
  await page.getByRole("button", { name: "Şarj adaylarını değerlendir" }).click();
  await expect(page.getByRole("heading", { name: "Bu grupta ürün yok." })).toBeVisible();
  await page.getByRole("tab", { name: /Doğrulama gerekli/ }).click();
  await expect(page.locator(".candidate")).toHaveCount(27);
});

test("photo inputs require actual analysis before confirmation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Fotoğraftan oku" }).click();
  await expect(page.getByRole("checkbox")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Fotoğrafları analiz et" })).toBeDisabled();
  await page.getByRole("button", { name: "Manuel giriş", exact: true }).click();
  await expect(page.getByRole("checkbox")).toBeEnabled();
});

test("mobile layout stays within viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Evinizi tanıyalım/ })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
