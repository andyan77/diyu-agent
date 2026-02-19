import { test, expect } from "@playwright/test";
import path from "node:path";

/**
 * Cross-layer FE E2E: File upload 3-step flow (XF2-3 partial).
 *
 * Phase 2 soft gate (TASK-INT-P2-FE).
 * Requires running backend with file storage configured.
 *
 * Covers:
 *   XF2-3 (partial): Drag-and-drop upload -> progress -> attachment in chat
 */

test.describe("Cross-layer: File Upload", () => {
  test.skip(
    !process.env.E2E_BACKEND_URL,
    "Requires E2E_BACKEND_URL; soft gate in Phase 2",
  );

  test("XF2-3: file input accepts and previews file", async ({ page }) => {
    await page.goto("/chat");

    const fileInput = page.getByTestId("file-input");
    await expect(fileInput).toBeAttached();

    // Upload a small test fixture
    const fixturePath = path.join(__dirname, "fixtures", "test-upload.txt");
    await fileInput.setInputFiles(fixturePath);

    // Preview should appear
    const preview = page.getByTestId("file-preview");
    await expect(preview).toBeVisible({ timeout: 5000 });
  });

  test("XF2-3: upload progress indicator renders", async ({ page }) => {
    await page.goto("/chat");

    const fileInput = page.getByTestId("file-input");
    const fixturePath = path.join(__dirname, "fixtures", "test-upload.txt");
    await fileInput.setInputFiles(fixturePath);

    // Trigger upload via send
    const input = page.getByTestId("message-input");
    await input.fill("Uploading file for cross-layer test");
    await page.getByTestId("send-button").click();

    // Progress bar or indicator should appear during upload
    const progress = page.getByTestId("upload-progress");
    // May already complete by the time we check; verify it existed or completed
    await expect(
      progress.or(page.getByTestId("upload-complete")),
    ).toBeVisible({ timeout: 10000 });
  });

  test("XF2-3: uploaded file appears as chat attachment", async ({ page }) => {
    await page.goto("/chat");

    const fileInput = page.getByTestId("file-input");
    const fixturePath = path.join(__dirname, "fixtures", "test-upload.txt");
    await fileInput.setInputFiles(fixturePath);

    const input = page.getByTestId("message-input");
    await input.fill("Check attachment rendering");
    await page.getByTestId("send-button").click();

    // Attachment indicator in sent message
    const attachment = page.getByTestId("message-attachment");
    await expect(attachment).toBeVisible({ timeout: 10000 });
    await expect(attachment).toContainText("test-upload");
  });
});
