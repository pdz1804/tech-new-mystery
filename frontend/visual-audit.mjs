import { chromium } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = 'http://localhost:3000';
const SCREENSHOTS_DIR = '../visual-audit-screenshots';

// Create screenshots directory
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

// Test configurations for different breakpoints
const BREAKPOINTS = {
  'mobile-375': { width: 375, height: 812, name: 'Mobile (375px - iPhone SE)' },
  'tablet-768': { width: 768, height: 1024, name: 'Tablet (768px - iPad)' },
  'desktop-1440': { width: 1440, height: 900, name: 'Desktop (1440px)' },
  'ultrawide-1920': { width: 1920, height: 1080, name: 'Ultra-wide (1920px)' },
};

// Test pages
const PAGES_TO_TEST = [
  { name: 'home', path: '/', waitFor: 'h1', desc: 'Home page' },
  { name: 'articles', path: '/articles', waitFor: '[data-testid="article-card"]', desc: 'Articles page', timeout: 8000 },
  { name: 'search', path: '/search', waitFor: 'input[type="text"]', desc: 'Search page' },
];

// Convert RGB to hex for easier reading
function rgbToHex(rgb) {
  if (!rgb || !rgb.includes('rgb')) return rgb;
  const match = rgb.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!match) return rgb;
  const r = parseInt(match[1]);
  const g = parseInt(match[2]);
  const b = parseInt(match[3]);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0').toUpperCase()}`;
}

// Validate colors
async function validateColors(page) {
  const colors = await page.evaluate(() => {
    const body = document.body;
    const bodyStyle = window.getComputedStyle(body);
    const h1 = document.querySelector('h1');
    const h1Style = h1 ? window.getComputedStyle(h1) : null;

    return {
      body: {
        backgroundColor: bodyStyle.backgroundColor,
        color: bodyStyle.color,
      },
      h1: h1Style ? {
        color: h1Style.color,
        fontSize: h1Style.fontSize,
        fontWeight: h1Style.fontWeight,
      } : null,
    };
  });

  return {
    body: {
      backgroundColor: rgbToHex(colors.body.backgroundColor),
      color: rgbToHex(colors.body.color),
    },
    h1: colors.h1 ? {
      color: rgbToHex(colors.h1.color),
      fontSize: colors.h1.fontSize,
      fontWeight: colors.h1.fontWeight,
    } : null,
  };
}

// Check typography hierarchy
async function checkTypography(page) {
  return await page.evaluate(() => {
    const h1 = document.querySelector('h1');
    const h2 = document.querySelector('h2');
    const h3 = document.querySelector('h3');
    const p = document.querySelector('p');

    const getTypography = (el) => {
      if (!el) return null;
      const style = window.getComputedStyle(el);
      return {
        fontSize: style.fontSize,
        fontWeight: style.fontWeight,
        lineHeight: style.lineHeight,
        color: style.color,
        text: el.innerText?.slice(0, 40),
      };
    };

    return {
      h1: getTypography(h1),
      h2: getTypography(h2),
      h3: getTypography(h3),
      body: getTypography(p),
    };
  });
}

// Check button styles
async function checkButtonStyles(page) {
  return await page.evaluate(() => {
    const buttons = document.querySelectorAll('button');
    return Array.from(buttons).slice(0, 3).map((btn) => {
      const style = window.getComputedStyle(btn);
      return {
        text: btn.innerText.slice(0, 20),
        backgroundColor: style.backgroundColor,
        color: style.color,
        boxShadow: style.boxShadow,
        borderRadius: style.borderRadius,
        padding: style.padding,
      };
    });
  });
}

// Check if backdrop filter is applied
async function checkGlassEffects(page) {
  return await page.evaluate(() => {
    const panels = document.querySelectorAll('[class*="glass"]');
    return Array.from(panels).slice(0, 3).map((el) => {
      const style = window.getComputedStyle(el);
      return {
        className: el.className.slice(0, 30),
        backdropFilter: style.backdropFilter,
        background: style.backgroundColor,
        border: style.borderColor,
      };
    });
  });
}

// Check modal/overlay darkening
async function checkBackdropBlur(page) {
  return await page.evaluate(() => {
    const modals = document.querySelectorAll('[class*="modal"], [class*="dialog"], [class*="backdrop"]');
    return {
      count: modals.length,
      examples: Array.from(modals).slice(0, 2).map((el) => {
        const style = window.getComputedStyle(el);
        return {
          className: el.className.slice(0, 30),
          backdropFilter: style.backdropFilter,
          backgroundColor: style.backgroundColor,
        };
      }),
    };
  });
}

// Check performance - frame drops
async function checkScrollPerformance(page) {
  const metrics = await page.evaluate(async () => {
    const initialTime = performance.now();

    // Simulate scrolling
    window.scrollBy(0, 500);
    await new Promise(r => setTimeout(r, 100));
    window.scrollBy(0, 500);
    await new Promise(r => setTimeout(r, 100));
    window.scrollBy(0, -1000);

    const endTime = performance.now();
    return {
      duration: endTime - initialTime,
      navigationTiming: {
        loadTime: performance.timing.loadEventEnd - performance.timing.navigationStart,
        domReady: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
      },
    };
  });
  return metrics;
}

async function runAudit() {
  const browser = await chromium.launch();
  const allResults = [];

  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║             TECH NEWS MYSTERY VISUAL AUDIT REPORT              ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  for (const [breakpointKey, viewport] of Object.entries(BREAKPOINTS)) {
    console.log(`\n┌─ TESTING: ${viewport.name}`);
    console.log('└─────────────────────────────────────────────────────────────────\n');

    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: 1,
    });

    const page = await context.newPage();
    const breakpointResults = {
      viewport: viewport.name,
      dimensions: `${viewport.width}x${viewport.height}`,
      pages: {},
    };

    for (const pageTest of PAGES_TO_TEST) {
      try {
        console.log(`  Testing: ${pageTest.desc}`);

        // Navigate to page
        await page.goto(`${BASE_URL}${pageTest.path}`, { waitUntil: 'networkidle' });

        // Wait for content
        try {
          await page.waitForSelector(pageTest.waitFor, { timeout: pageTest.timeout || 5000 });
        } catch (e) {
          console.warn(`    ⚠ Selector timeout: ${pageTest.waitFor}`);
        }

        // Collect metrics
        const colors = await validateColors(page);
        const typography = await checkTypography(page);
        const buttons = await checkButtonStyles(page);
        const glassEffects = await checkGlassEffects(page);
        const performance = await checkScrollPerformance(page);

        // Log results
        console.log(`    Colors:`);
        console.log(`      Body BG: ${colors.body.backgroundColor}`);
        console.log(`      Body Text: ${colors.body.color}`);
        if (colors.h1) {
          console.log(`      H1 Color: ${colors.h1.color}`);
          console.log(`      H1 Size: ${colors.h1.fontSize}`);
        }

        if (typography.h1) {
          console.log(`    Typography:`);
          console.log(`      H1: ${typography.h1.fontSize} (weight: ${typography.h1.fontWeight})`);
          if (typography.h2) console.log(`      H2: ${typography.h2.fontSize}`);
          if (typography.h3) console.log(`      H3: ${typography.h3.fontSize}`);
          if (typography.body) console.log(`      Body: ${typography.body.fontSize}`);
        }

        console.log(`    Buttons: ${buttons.length} found`);
        if (buttons.length > 0) {
          const btnBg = rgbToHex(buttons[0].backgroundColor);
          const btnShadow = buttons[0].boxShadow;
          console.log(`      Primary: BG=${btnBg}, Shadow=${btnShadow.slice(0, 40)}...`);
        }

        console.log(`    Glass Effects: ${glassEffects.length} panels`);
        if (glassEffects.length > 0) {
          console.log(`      Blur: ${glassEffects[0].backdropFilter || 'NONE'}`);
          console.log(`      BG: ${rgbToHex(glassEffects[0].background)}`);
        }

        console.log(`    Performance: Load=${performance.navigationTiming.loadTime.toFixed(0)}ms`);

        // Take screenshot
        const screenshotName = `${pageTest.name}-${breakpointKey}`;
        const screenshotPath = path.join(SCREENSHOTS_DIR, `${screenshotName}.png`);
        await page.screenshot({
          path: screenshotPath,
          fullPage: false,
        });
        console.log(`    ✓ Screenshot saved\n`);

        breakpointResults.pages[pageTest.name] = {
          colors,
          typography,
          buttons: buttons.length,
          glassEffects: glassEffects.length,
          performance,
        };
      } catch (error) {
        console.error(`    ✗ Error: ${error.message}\n`);
      }
    }

    allResults.push(breakpointResults);
    await context.close();
  }

  await browser.close();

  // Save detailed report
  const reportPath = path.join(SCREENSHOTS_DIR, 'audit-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(allResults, null, 2));

  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║                       AUDIT COMPLETED                          ║');
  console.log(`║  Screenshots: ${SCREENSHOTS_DIR}                      ║`);
  console.log(`║  Report: ${reportPath.slice(-35).padEnd(35)}║`);
  console.log('╚════════════════════════════════════════════════════════════════╝\n');
}

runAudit().catch(console.error);
