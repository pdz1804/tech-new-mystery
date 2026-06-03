const { chromium } = require('playwright');

async function run() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 920 } });
  await context.grantPermissions(['microphone']);
  const page = await context.newPage();

  await page.route('**/v1/chat/sessions**', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              session_id: 'visual-voice-session',
              user_id: 'visual-smoke-user',
              title: 'Voice agent session',
              description: 'Dedicated voice-agent testing session',
              message_count: 0,
              created_at: 1760000000,
              updated_at: 1760000000,
              last_message_at: 1760000000,
            },
          ],
          meta: { page: 1, limit: 50, total: 1 },
        }),
      });
      return;
    }
    await route.continue();
  });

  await page.route('**/v1/auth/me', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          user_id: 'visual-smoke-user',
          username: 'visual-smoke',
          email: 'visual-smoke@example.com',
          role: 'user',
          is_active: true,
          created_at: 1760000000,
        },
      }),
    });
  });

  await page.route('**/v1/chat/voice/livekit-session', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          transport: 'livekit',
          server_url: 'wss://visual-smoke.livekit.cloud',
          room: 'voice-visual-smoke',
          participant_token: 'visual-token',
          agent_name: 'tech-news-voice-agent',
          trace_id: 'visual-trace',
          expires_in: 900,
        },
      }),
    });
  });

  await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    window.localStorage.setItem(
      'auth-storage',
      JSON.stringify({
        state: {
          accessToken: 'visual-smoke-token',
          user: {
            user_id: 'visual-smoke-user',
            username: 'visual-smoke',
            email: 'visual-smoke@example.com',
            role: 'user',
          },
          isAuthenticated: true,
          intendedDestination: null,
        },
        version: 0,
      })
    );
  });

  await page.reload({ waitUntil: 'networkidle' });
  await page.screenshot({ path: 'tests/visual/floating-voice-bot-before-wait.png', fullPage: true });
  await page.getByLabel('Open voice agent').waitFor({ state: 'visible', timeout: 10000 });
  await page.screenshot({ path: 'tests/visual/floating-voice-bot-desktop.png', fullPage: true });

  await page.getByLabel('Open voice agent').click();
  await page.getByText('Tech News Voice').waitFor({ state: 'visible', timeout: 10000 });
  await page.screenshot({ path: 'tests/visual/floating-voice-bot-panel-desktop.png', fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: 'tests/visual/floating-voice-bot-panel-mobile.png', fullPage: true });

  await context.close();
  await browser.close();
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
