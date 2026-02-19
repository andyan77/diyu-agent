import { test, expect } from "@playwright/test";

/**
 * Cross-layer FE E2E: File upload 3-step flow (XF2-3 partial).
 *
 * Phase 2 hard gate (TASK-INT-P2-FE).
 * Tests the FileUpload component integration with chat page.
 *
 * Covers:
 *   XF2-3 (partial): File input -> upload trigger -> status display
 *
 * Architecture: FileUpload renders a drop-zone with hidden file input
 * (data-testid="file-input"). After file selection, it calls onUpload()
 * and shows upload status via upload-list / upload-status-{id} elements.
 * The chat page's onUpload is a placeholder that returns a UUID immediately.
 */

test.describe("Cross-layer: File Upload", () => {
  test("XF2-3: file upload component renders in chat", async ({ page }) => {
    await page.goto("/chat");

    // File upload component should be present
    const fileUpload = page.getByTestId("file-upload");
    await expect(fileUpload).toBeVisible({ timeout: 5000 });

    // Drop zone should be visible
    const dropZone = page.getByTestId("drop-zone");
    await expect(dropZone).toBeVisible();

    // Hidden file input should be attached
    const fileInput = page.getByTestId("file-input");
    await expect(fileInput).toBeAttached();
  });

  test("XF2-3: file input accepts file and shows upload status", async ({
    page,
  }) => {
    await page.goto("/chat");

    const fileInput = page.getByTestId("file-input");
    await expect(fileInput).toBeAttached();

    // Create a small test file buffer to upload
    await fileInput.setInputFiles({
      name: "test-upload.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Cross-layer file upload test content"),
    });

    // Upload list should appear with the file
    const uploadList = page.getByTestId("upload-list");
    await expect(uploadList).toBeVisible({ timeout: 5000 });

    // File name should be displayed in upload list
    await expect(uploadList).toContainText("test-upload.txt");
  });

  test("XF2-3: upload completes with done status", async ({ page }) => {
    await page.goto("/chat");

    const fileInput = page.getByTestId("file-input");

    await fileInput.setInputFiles({
      name: "test-doc.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Test document for upload status verification"),
    });

    // Wait for upload to complete (placeholder onUpload resolves immediately)
    const uploadList = page.getByTestId("upload-list");
    await expect(uploadList).toBeVisible({ timeout: 5000 });

    // Status should show "done" after completion
    await expect(uploadList).toContainText("done", { timeout: 5000 });
  });
});
