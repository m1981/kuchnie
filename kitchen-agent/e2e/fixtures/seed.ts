import { Page } from '@playwright/test';

/**
 * Seed API response type
 */
export interface SeedResult {
  session_id: string;
  message_count: number;
  turn_ids: Array<{ user: string; assistant: string }>;
}

/**
 * Seed options for creating test sessions
 */
export interface SeedOptions {
  pairs: number;
  title?: string;
}

/**
 * Seed a test session via the backend API.
 * Requires DEBUG=true on the backend.
 *
 * @param page - Playwright Page object (used for API context)
 * @param options - Seed options
 * @returns SeedResult with session_id and turn_ids
 */
export async function seedSession(
  page: Page,
  options: SeedOptions
): Promise<SeedResult & { title: string }> {
  const title = options.title || `E2E Test ${Date.now()}`;

  const response = await page.request.post('http://localhost:8000/api/_test/seed', {
    data: {
      pairs: options.pairs,
      title,
    },
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(`Seed failed: ${response.status()} ${body}`);
  }

  const data = await response.json();
  return {
    ...data,
    title,
  };
}

/**
 * Delete a session via the backend API (cleanup).
 */
export async function deleteSession(page: Page, sessionId: string): Promise<void> {
  await page.request.delete(`http://localhost:8000/api/sessions/${sessionId}`);
}

/**
 * Get session state via the backend API.
 */
export async function getSessionState(
  page: Page,
  sessionId: string
): Promise<{
  session_id: string;
  message_count: number;
  turn_ids: string[];
  roles: string[];
}> {
  const response = await page.request.get(`http://localhost:8000/api/sessions/${sessionId}/state`);
  return response.json();
}
