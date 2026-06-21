import { test, expect } from '@playwright/test';
import { ChatPage } from '../../page-objects/ChatPage';
import { SidebarPage } from '../../page-objects/SidebarPage';
import { ComposerPage } from '../../page-objects/ComposerPage';

test.describe('Desktop Layout @smoke @desktop', () => {
    let chatPage: ChatPage;
    let sidebarPage: SidebarPage;
    let composerPage: ComposerPage;

    test.beforeEach(async ({ page }) => {
        chatPage = new ChatPage(page);
        sidebarPage = new SidebarPage(page);
        composerPage = new ComposerPage(page);

        await page.goto('/');
        await page.waitForLoadState('networkidle');
    });

    test('three-panel layout renders correctly', async ({ page }) => {
        // Left sidebar visible
        await sidebarPage.expectVisible();

        // Main chat area visible
        await expect(chatPage.chatInput).toBeVisible();

        // Right sidebar visible (context panel)
        const rightPanel = page.locator('aside').last();
        await expect(rightPanel).toBeVisible();
    });

    test('sidebar toggle hides left panel', async () => {
        // Initially visible
        await sidebarPage.expectVisible();
        await sidebarPage.expectToggleLabel('Hide sidebar');

        // Toggle to hide
        await sidebarPage.toggle();

        // Sidebar hidden
        await sidebarPage.expectHidden();
        await sidebarPage.expectToggleLabel('Show sidebar');
    });

    test('sidebar toggle shows left panel', async () => {
        // First hide
        await sidebarPage.toggle();
        await sidebarPage.expectHidden();

        // Toggle to show
        await sidebarPage.toggle();

        // Sidebar visible
        await sidebarPage.expectVisible();
        await sidebarPage.expectToggleLabel('Hide sidebar');
    });

    test('system prompt collapsed by default', async () => {
        // System prompt bubble visible
        await chatPage.expectSystemPromptVisible();

        // Should be collapsed (no textarea or pre visible)
        await chatPage.expectSystemPromptCollapsed();
    });

    test('composer ready for input', async () => {
        await composerPage.expectReady();
        await composerPage.expectSendDisabled();
    });

    test('tools toggle works', async () => {
        // Initially enabled (blue)
        await composerPage.expectToolsState(true);

        // Toggle off
        await composerPage.toggleTools();
        await composerPage.expectToolsState(false);

        // Toggle back on
        await composerPage.toggleTools();
        await composerPage.expectToolsState(true);
    });
});
