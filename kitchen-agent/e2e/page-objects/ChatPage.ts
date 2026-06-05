import { Page, Locator, expect } from '@playwright/test';

/**
 * Page Object for the Chat application.
 * Encapsulates all page interactions for maintainable E2E tests.
 */
export class ChatPage {
  readonly page: Page;

  // ── Locators ──────────────────────────────────────────────────
  readonly chatBubbles: Locator;
  readonly userBubbles: Locator;
  readonly assistantBubbles: Locator;
  readonly editButtons: Locator;
  readonly deleteButtons: Locator;
  readonly deletePairButtons: Locator;
  readonly forkButtons: Locator;
  readonly confirmDialog: Locator;
  readonly confirmOkButton: Locator;
  readonly confirmCancelButton: Locator;
  readonly busyIndicator: Locator;
  readonly loadingIndicator: Locator;
  readonly truncateBar: Locator;
  readonly truncateButtons: Locator;
  readonly chatInput: Locator;
  readonly sendButton: Locator;

  constructor(page: Page) {
    this.page = page;

    // Message bubbles
    this.chatBubbles = page.getByTestId('chat-bubble');
    this.userBubbles = page.getByTestId('chat-bubble').filter({ has: page.locator('[data-chat-bubble="user"]') });
    this.assistantBubbles = page.getByTestId('chat-bubble').filter({ has: page.locator('[data-chat-bubble="assistant"]') });

    // Action buttons (scoped to avoid conflicts)
    this.editButtons = page.getByTestId('edit-btn');
    this.deleteButtons = page.getByTestId('delete-btn');
    this.deletePairButtons = page.getByTestId('delete-pair-btn');
    this.forkButtons = page.getByTestId('fork-btn');

    // Confirm dialog
    this.confirmDialog = page.getByTestId('confirm-dialog');
    this.confirmOkButton = page.getByTestId('confirm-ok');
    this.confirmCancelButton = page.getByTestId('confirm-cancel');

    // State indicators
    this.busyIndicator = page.getByTestId('app-busy');
    this.loadingIndicator = page.getByTestId('loading-indicator');

    // Truncation
    this.truncateBar = page.getByTestId('truncate-bar');
    this.truncateButtons = page.getByTestId('truncate-btn');

    // Composer
    this.chatInput = page.getByTestId('chat-input');
    this.sendButton = page.getByTestId('send-btn');
  }

  // ── Navigation ────────────────────────────────────────────────

  async goto() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  async loadSession(title: string) {
    // Wait for sidebar to load
    await this.page.waitForSelector('aside button', { timeout: 10_000 });
    
    // Try to find and click the session - use first match to avoid strict mode
    let sessionButton = this.page.locator(`aside button:has-text("${title}")`).first();
    
    // If not visible, refresh and wait (session might have been seeded after page load)
    const isVisible = await sessionButton.isVisible().catch(() => false);
    if (!isVisible) {
      await this.page.reload();
      await this.page.waitForLoadState('networkidle');
      await this.page.waitForSelector('aside button', { timeout: 10_000 });
      sessionButton = this.page.locator(`aside button:has-text("${title}")`).first();
    }
    
    // Wait for the button to appear
    await sessionButton.waitFor({ state: 'visible', timeout: 10_000 });
    await sessionButton.click();
    await this.waitForMessagesLoaded();
  }

  // ── Waits ─────────────────────────────────────────────────────

  async waitForMessagesLoaded(minCount: number = 1) {
    await this.page.waitForFunction(
      (count) => document.querySelectorAll('[data-testid="chat-bubble"]').length >= count,
      minCount,
      { timeout: 10_000 }
    );
  }

  async waitForBusyComplete() {
    // Wait for data-busy-recent to become 'false'
    await this.page.waitForFunction(
      () => {
        const el = document.querySelector('[data-testid="app-busy"]');
        return el?.getAttribute('data-busy-recent') === 'false';
      },
      { timeout: 10_000 }
    );
  }

  async waitForConfirmDialog() {
    await this.confirmDialog.waitFor({ state: 'visible', timeout: 5_000 });
  }

  // ── Message Actions ───────────────────────────────────────────

  async getMessageCount(): Promise<number> {
    return this.chatBubbles.count();
  }

  async getMessageText(index: number): Promise<string> {
    const text = await this.chatBubbles.nth(index).textContent();
    return text?.trim() || '';
  }

  async getMessageRole(index: number): Promise<string> {
    return this.chatBubbles.nth(index).getAttribute('data-chat-bubble') || '';
  }

  async deleteMessage(index: number) {
    await this.deleteButtons.nth(index).click();
    await this.waitForConfirmDialog();
    await this.confirmOkButton.click();
    await this.waitForBusyComplete();
  }

  async deletePair(index: number) {
    await this.deletePairButtons.nth(index).click();
    await this.waitForConfirmDialog();
    await this.confirmOkButton.click();
    await this.waitForBusyComplete();
  }

  async cancelDelete(index: number) {
    await this.deleteButtons.nth(index).click();
    await this.waitForConfirmDialog();
    await this.confirmCancelButton.click();
  }

  // ── Assertions ────────────────────────────────────────────────

  async expectMessageCount(count: number) {
    await expect(this.chatBubbles).toHaveCount(count, { timeout: 10_000 });
  }

  async expectMessageText(index: number, text: string) {
    await expect(this.chatBubbles.nth(index)).toContainText(text);
  }

  async expectButtonDisabled(testid: string, index: number = 0) {
    const button = this.page.getByTestId(testid).nth(index);
    await expect(button).toBeDisabled();
  }

  async expectButtonEnabled(testid: string, index: number = 0) {
    const button = this.page.getByTestId(testid).nth(index);
    await expect(button).toBeEnabled();
  }

  async expectConfirmDialogVisible() {
    await expect(this.confirmDialog).toBeVisible();
  }

  async expectConfirmDialogHidden() {
    await expect(this.confirmDialog).toBeHidden();
  }
}
