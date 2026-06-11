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
  readonly moreOptionsButtons: Locator;
  readonly deleteButtons: Locator;
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

  // Header
  readonly headerTitle: Locator;
  readonly headerTitleInput: Locator;
  readonly headerModeBadge: Locator;

  // Token Indicator
  readonly tokenProgressBar: Locator;
  readonly tokenCount: Locator;
  readonly inputTokenEstimate: Locator;

  constructor(page: Page) {
    this.page = page;

    // Message bubbles
    this.chatBubbles = page.getByTestId('chat-bubble');
    this.userBubbles = page.getByTestId('chat-bubble').filter({ has: page.locator('[data-chat-bubble="user"]') });
    this.assistantBubbles = page.getByTestId('chat-bubble').filter({ has: page.locator('[data-chat-bubble="assistant"]') });

    // Action buttons (scoped to avoid conflicts)
    this.editButtons = page.getByTestId('edit-btn');
    this.moreOptionsButtons = page.getByTestId('more-options-btn');
    this.deleteButtons = page.getByTestId('delete-btn');
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

    // Header
    this.headerTitle = page.locator('header button, header h2').first();
    this.headerTitleInput = page.locator('header input');
    this.headerModeBadge = page.locator('header span:has-text("General")');

    // Token Indicator
    this.tokenProgressBar = page.locator('[role="progressbar"]');
    this.tokenCount = page.locator('text=/📊/');
    this.inputTokenEstimate = page.locator('text=/→/');
  }

  // ── Navigation ────────────────────────────────────────────────

  async goto() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  async gotoSession(sessionId: string) {
    await this.page.goto(`/chat/${sessionId}`);
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
    // Click the more options button for this message to open the dropdown
    await this.moreOptionsButtons.nth(index).click();
    // Wait for the dropdown menu to appear
    await this.page.waitForSelector('[data-testid="delete-btn"]', { state: 'visible', timeout: 5_000 });
    // Click the delete button in the dropdown
    await this.deleteButtons.first().click();
    await this.waitForConfirmDialog();
    await this.confirmOkButton.click();
    await this.waitForBusyComplete();
  }

  async cancelDelete(index: number) {
    // Click the more options button for this message to open the dropdown
    await this.moreOptionsButtons.nth(index).click();
    // Wait for the dropdown menu to appear
    await this.page.waitForSelector('[data-testid="delete-btn"]', { state: 'visible', timeout: 5_000 });
    // Click the delete button in the dropdown
    await this.deleteButtons.first().click();
    await this.waitForConfirmDialog();
    await this.confirmCancelButton.click();
  }

  // ── Title Actions ─────────────────────────────────────────────

  async editTitle(newTitle: string) {
    // Click on the title to start editing
    await this.headerTitle.click();
    
    // Wait for input to appear
    await this.headerTitleInput.waitFor({ state: 'visible', timeout: 2000 });
    
    // Clear and type new title
    await this.headerTitleInput.clear();
    await this.headerTitleInput.fill(newTitle);
    
    // Press Enter to save
    await this.headerTitleInput.press('Enter');
    
    // Wait for save to complete
    await this.page.waitForTimeout(500);
  }

  async cancelEditTitle() {
    await this.headerTitleInput.press('Escape');
  }

  async getTitleText(): Promise<string> {
    const text = await this.headerTitle.textContent();
    return text?.trim() || '';
  }

  // ── Token Indicator ───────────────────────────────────────────

  async getTokenPercentage(): Promise<string> {
    const text = await this.tokenProgressBar.locator('..').locator('..').textContent();
    const match = text?.match(/(\d+)%/);
    return match ? match[1] : '0';
  }

  // ── Context Menu ──────────────────────────────────────────────

  async openSessionContextMenu(sessionTitle: string) {
    // Find the session in sidebar
    const sessionItem = this.page.locator(`aside button:has-text("${sessionTitle}")`).locator('..');
    
    // Find and click the ⋯ button
    const menuButton = sessionItem.locator('button[aria-label="Session options"]');
    await menuButton.click();
    
    // Wait for menu to appear
    await this.page.waitForTimeout(200);
  }

  async clickRegenerateTitle() {
    const regenerateButton = this.page.locator('button:has-text("Regenerate Title")');
    await regenerateButton.click();
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

  async expectTitleToContain(text: string) {
    const header = this.page.locator('header');
    await expect(header).toContainText(text);
  }

  async expectTokenIndicatorVisible() {
    await expect(this.tokenProgressBar).toBeVisible();
    await expect(this.tokenCount).toBeVisible();
    await expect(this.inputTokenEstimate).toBeVisible();
  }
}
