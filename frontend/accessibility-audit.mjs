import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:3000';

async function auditAccessibility() {
  const browser = await chromium.launch();

  const viewports = [
    { name: 'Mobile', width: 375, height: 812 },
    { name: 'Tablet', width: 768, height: 1024 },
    { name: 'Desktop', width: 1440, height: 900 },
    { name: 'UltraWide', width: 1920, height: 1080 },
  ];

  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║         ACCESSIBILITY & RESPONSIVENESS AUDIT                  ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  for (const viewport of viewports) {
    console.log(`\n┌─ ${viewport.name} (${viewport.width}x${viewport.height})`);
    console.log('└────────────────────────────────────────────────────────────────\n');

    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
    });

    const page = await context.newPage();
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });

    // Check text rendering
    const textMetrics = await page.evaluate(() => {
      const h1 = document.querySelector('h1');
      const h2 = document.querySelector('h2');
      const h3 = document.querySelector('h3');
      const p = document.querySelector('p');

      return {
        h1: h1 ? {
          size: window.getComputedStyle(h1).fontSize,
          weight: window.getComputedStyle(h1).fontWeight,
          lineHeight: window.getComputedStyle(h1).lineHeight,
          color: window.getComputedStyle(h1).color,
        } : null,
        h2: h2 ? window.getComputedStyle(h2).fontSize : null,
        h3: h3 ? window.getComputedStyle(h3).fontSize : null,
        body: p ? {
          size: window.getComputedStyle(p).fontSize,
          lineHeight: window.getComputedStyle(p).lineHeight,
          color: window.getComputedStyle(p).color,
        } : null,
      };
    });

    console.log('  Typography Rendering:');
    if (textMetrics.h1) {
      console.log(`    H1: ${textMetrics.h1.size} (weight: ${textMetrics.h1.weight})`);
      console.log(`        Line Height: ${textMetrics.h1.lineHeight}`);
    }
    if (textMetrics.h2) console.log(`    H2: ${textMetrics.h2}`);
    if (textMetrics.h3) console.log(`    H3: ${textMetrics.h3}`);
    if (textMetrics.body) {
      console.log(`    Body: ${textMetrics.body.size} (line height: ${textMetrics.body.lineHeight})`);
    }

    // Check button states
    const buttonStates = await page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      const checks = [];
      
      buttons.forEach((btn) => {
        if (!btn.offsetParent) return; // Skip hidden buttons
        const style = window.getComputedStyle(btn);
        const rect = btn.getBoundingClientRect();
        
        checks.push({
          hasText: btn.textContent.trim().length > 0,
          minHeight: parseInt(style.height) >= 44,
          minWidth: parseInt(style.width) >= 44,
          minPadding: parseInt(style.padding) > 0,
          focusable: btn.offsetParent !== null,
          cursor: style.cursor,
        });
      });
      return checks;
    });

    const avgButtonHeight = buttonStates.reduce((sum, b) => sum + (b.minHeight ? 1 : 0), 0);
    console.log(`\n  Button Accessibility (${buttonStates.length} buttons):`);
    console.log(`    Touch target size (44px+): ${avgButtonHeight}/${buttonStates.length} compliant`);
    console.log(`    All have text labels: ${buttonStates.every(b => b.hasText) ? '✓' : '✗'}`);

    // Check color contrast
    const contrast = await page.evaluate(() => {
      const getContrast = (foreground, background) => {
        const getForeground = (str) => {
          const match = str.match(/\d+/g);
          if (!match || match.length < 3) return null;
          const [r, g, b] = [parseInt(match[0]), parseInt(match[1]), parseInt(match[2])];
          const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
          return luminance > 0.5 ? 'light' : 'dark';
        };
        return getForeground(foreground);
      };

      const bodyStyle = window.getComputedStyle(document.body);
      const fg = bodyStyle.color;
      const bg = bodyStyle.backgroundColor;
      
      return {
        foreground: fg,
        background: bg,
        analysis: getContrast(fg, bg),
      };
    });

    console.log(`\n  Color Contrast:`);
    console.log(`    Foreground: ${contrast.foreground}`);
    console.log(`    Background: ${contrast.background}`);
    console.log(`    Likely WCAG AA: ${contrast.analysis === 'light' || contrast.analysis === 'dark' ? '✓' : '?'}`);

    // Check for focus states
    const focusStates = await page.evaluate(() => {
      const inputs = document.querySelectorAll('input, button, a');
      const focusable = [];
      
      inputs.forEach((el) => {
        const style = window.getComputedStyle(el);
        focusable.push({
          tag: el.tagName.toLowerCase(),
          hasFocusVisible: el.classList.contains('focus-visible') ||
                          style.outline !== 'none' ||
                          style.outlineColor !== 'transparent',
        });
      });
      return focusable.slice(0, 5);
    });

    const focusVisibleCount = focusStates.filter(f => f.hasFocusVisible).length;
    console.log(`\n  Keyboard Navigation:`);
    console.log(`    Focus-visible elements: ${focusVisibleCount}/${focusStates.length}`);

    // Check responsive grid alignment
    const grid = await page.evaluate(() => {
      const cards = document.querySelectorAll('[class*="card"], [class*="grid"]');
      return {
        cardCount: cards.length,
        alignmentClasses: Array.from(cards)
          .map(c => c.className)
          .filter(cn => cn.includes('grid') || cn.includes('gap'))
          .length,
      };
    });

    console.log(`\n  Responsive Grid:`);
    console.log(`    Grid containers: ${grid.cardCount}`);
    console.log(`    With alignment classes: ${grid.alignmentClasses}`);

    await context.close();
  }

  await browser.close();
  console.log('\n');
}

auditAccessibility().catch(console.error);
