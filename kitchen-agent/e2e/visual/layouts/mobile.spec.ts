import { test, expect } from '@playwright/test';
import { ChatPage } from '../../page-objects/ChatPage';
import { ComposerPage } from '../../page-objects/ComposerPage';

test.describe('Mobile Layout @smoke @mobile', () => {
    let chatPage: ChatPage;
    let composerPage: ComposerPage;

    test.beforeEach(async ({ page }) => {
        // Clear localStorage for consistent state
        await page.goto('/');
        await page.evaluate(() => localStorage.clear());

        // Set iPhone 13 viewport
        await page.setViewportSize({ width: 390, height: 844 });

        chatPage = new ChatPage(page);
        composerPage = new ComposerPage(page);

        // Reload after clearing localStorage
        await page.goto('/');
        await page.waitForLoadState('networkidle');
    });

    test('sidebar hidden on mobile', async ({ page }) => {
        // Left sidebar should not be visible on mobile
        const sidebar = page.locator('aside').first();
        await expect(sidebar).toBeHidden();
    });

    test('sidebar toggle hidden on mobile', async ({ page }) => {
        // Toggle button should not be visible on mobile
        const toggle = page.getByTestId('sidebar-toggle');
        await expect(toggle).toBeHidden();
    });

    test('chat fills full viewport on mobile', async ({ page }) => {
        // Main area should fill viewport
        const main = page.locator('main');
        const box = await main.boundingBox();
        expect(box?.width).toBeGreaterThanOrEqual(350);
    });

    test('composer accessible on mobile', async () => {
        await composerPage.expectReady();
    });

    test('system prompt visible on mobile', async () => {
        await chatPage.expectSystemPromptVisible();
    });

    test('system prompt collapsed on mobile', async () => {
        await chatPage.expectSystemPromptCollapsed();
    });

    test('send button visible on mobile', async ({ page }) => {
        const sendBtn = page.getByTestId('send-btn');
        await expect(sendBtn).toBeVisible();
    });

    test('tools toggle visible on mobile', async ({ page }) => {
        const tools = page.getByTestId('tools-toggle');
        await expect(tools).toBeVisible();
    });
});
