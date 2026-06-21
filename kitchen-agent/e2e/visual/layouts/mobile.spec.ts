import { test, expect, devices } from '@playwright/test';
import { ChatPage } from '../../page-objects/ChatPage';
import { SidebarPage } from '../../page-objects/SidebarPage';
import { ComposerPage } from '../../page-objects/ComposerPage';

test.describe('Mobile Layout @smoke @mobile', () => {
    let chatPage: ChatPage;
    let sidebarPage: SidebarPage;
    let composerPage: ComposerPage;

    test.beforeEach(async ({ page }) => {
        // Set iPhone 13 viewport
        await page.setViewportSize({ width: 390, height: 844 });

        chatPage = new ChatPage(page);
        sidebarPage = new SidebarPage(page);
        composerPage = new ComposerPage(page);

        await page.goto('/');
        await page.waitForLoadState('networkidle');
    });

    test('sidebar hidden by default on mobile', async () => {
        await sidebarPage.expectHidden();
    });

    test('toggle button visible on mobile', async () => {
        await expect(sidebarPage.toggleButton).toBeVisible();
    });

    test('sidebar opens as overlay with backdrop', async () => {
        // Open sidebar
        await sidebarPage.toggle();

        // Sidebar visible
        await sidebarPage.expectVisible();

        // Backdrop visible
        await expect(sidebarPage.mobileBackdrop).toBeVisible();
    });

    test('backdrop tap closes sidebar', async () => {
        // Open sidebar
        await sidebarPage.toggle();
        await sidebarPage.expectVisible();

        // Tap backdrop
        await sidebarPage.closeViaBackdrop();

        // Sidebar hidden
        await sidebarPage.expectHidden();
    });

    test('toggle button closes sidebar', async () => {
        // Open sidebar
        await sidebarPage.toggle();
        await sidebarPage.expectVisible();

        // Close via toggle
        await sidebarPage.toggle();

        // Sidebar hidden
        await sidebarPage.expectHidden();
    });

    test('chat fills viewport when sidebar closed', async ({ page }) => {
        // Sidebar closed by default
        await sidebarPage.expectHidden();

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
});
