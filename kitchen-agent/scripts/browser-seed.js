#!/usr/bin/env node

/**
 * browser-seed.js
 * ================
 * Create a test session with N turn-pairs and navigate to it.
 *
 * Usage:
 *   browser-seed.js --pairs 3
 *   browser-seed.js --pairs 2 --title "My test session"
 *   browser-seed.js --pairs 1 --api http://localhost:8000
 *
 * Options:
 *   --pairs N       Number of turn-pairs to create (default: 2)
 *   --title <str>   Custom session title
 *   --api <url>     Backend API URL (default: http://localhost:8000)
 *
 * Output:
 *   session_id, message_count, turn_ids
 */

import puppeteer from 'puppeteer-core';

const args = process.argv.slice(2);

function getArg(name) {
    const idx = args.indexOf(`--${name}`);
    if (idx === -1) return null;
    return args[idx + 1];
}

const pairs = parseInt(getArg('pairs') || '2', 10);
const title = getArg('title') || null;
const apiBase = getArg('api') || 'http://localhost:8000';

if (pairs < 1 || pairs > 20) {
    console.error('✗ --pairs must be between 1 and 20');
    process.exit(1);
}

async function seedSession() {
    // Call the seed endpoint
    const body = { pairs, title };
    const res = await fetch(`${apiBase}/api/_test/seed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });

    if (!res.ok) {
        const text = await res.text();
        if (res.status === 404) {
            console.error('✗ Seed endpoint not found. Ensure DEBUG=true is set in .env');
        } else {
            console.error(`✗ Seed failed: ${res.status} ${text}`);
        }
        process.exit(1);
    }

    return res.json();
}

async function connectBrowser() {
    const b = await Promise.race([
        puppeteer.connect({
            browserURL: 'http://localhost:9222',
            defaultViewport: null
        }),
        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 5000))
    ]).catch((e) => {
        console.error('✗ Could not connect to browser:', e.message);
        process.exit(1);
    });

    const p = (await b.pages()).at(-1);
    if (!p) {
        console.error('✗ No active tab found');
        await b.disconnect();
        process.exit(1);
    }

    return { browser: b, page: p };
}

async function run() {
    // Seed the session
    const data = await seedSession();

    // Connect to browser and navigate
    const { browser, page } = await connectBrowser();

    try {
        // Navigate to the frontend
        const frontendUrl = 'http://localhost:5173';
        await page.goto(frontendUrl, { waitUntil: 'domcontentloaded' });

        // Wait for the page to load
        await page.waitForSelector('aside button', { timeout: 5000 });

        // Click the session in the sidebar (it should appear after refresh)
        // First, trigger a refresh by clicking on the session
        await page.evaluate((sid) => {
            // Wait a bit for the session list to refresh
            return new Promise((resolve) => setTimeout(resolve, 500));
        }, data.session_id);

        // Click the first "Test session" button in the sidebar
        const clicked = await page.evaluate((title) => {
            const buttons = Array.from(document.querySelectorAll('aside button'));
            const btn = buttons.find(
                (b) =>
                    b.textContent.trim().includes('Test session') ||
                    (title && b.textContent.trim().includes(title))
            );
            if (btn) {
                btn.click();
                return true;
            }
            return false;
        }, title);

        if (!clicked) {
            // If not found, try clicking the first session-like button
            await page.evaluate(() => {
                const buttons = Array.from(document.querySelectorAll('aside button'));
                const nonNewChat = buttons.filter(
                    (b) => b.textContent.trim() !== '+ New chat' && b.textContent.trim() !== ''
                );
                if (nonNewChat.length > 0) {
                    nonNewChat[0].click();
                }
            });
        }

        // Output the result
        console.log(`✓ Seeded session: ${data.session_id}`);
        console.log(`  Messages: ${data.message_count}`);
        console.log(`  Turn pairs: ${JSON.stringify(data.turn_ids, null, 2)}`);
    } finally {
        await browser.disconnect();
    }
}

run().catch((e) => {
    console.error('✗ Error:', e.message);
    process.exit(1);
});
