import { chromium } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = 'http://localhost:3000';
const SCREENSHOTS_DIR = './visual-audit-screenshots';

// Create screenshots directory
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

// Test configurations for different breakpoints
const BREAKPOINTS = {
  'mobile-iphone-se': { width: 375, height: 812, name: 'iPhone SE (375px)' },
  'tablet-ipad': { width: 768, height: 1024, name: 'iPad (768px)' },
  'desktop-standard': { width: 1440, height: 900, name: 'Standard Desktop (1440px)' },
  'desktop-ultrawide': { width: 1920, height: 1080, name: 'Ultra-wide (1920px)' },
};

// Test pages
const PAGES_TO_TEST = [
  { name: 'home', path: '/', waitFor: 'h1' },
  { name: 'login', path: '/login', waitFor: 'input[type="email"]' },
  { name: 'articles', path: '/articles', waitFor: 'h1', requireAuth: true },
  { name: 'search', path: '/search', waitFor: 'input[type="text"]', requireAuth: true },
];

// Color validation helper
async function validateColors(page, viewport) {
  const bodyStyle = await page.evaluate(() => {
    const body = document.body;
    return {
      backgroundColor: window.getComputedStyle(body).backgroundColor,
      color: window.getComputedStyle(body).color,
    };
  });

  return bodyStyle;
}

// Text contrast checker
async function checkContrast(page, selector) {
  try {
    const contrast = await page.evaluate((sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const style = window.getComputedStyle(el);
      return {
        color: style.color,
        backgroundColor: style.backgroundColor,
        fontSize: style.fontSize,
        fontWeight: style.fontWeight,
      };
    }, selector);
    return contrast;
  } catch (e) {
    return null;
  }
}

// Check button styles
async function checkButtonStyles(page) {
  const buttons = await page.evaluate(() => {
    const btns = document.querySelectorAll('button');
    return Array.from(btns).slice(0, 3).map((btn) => {
      const style = window.getComputedStyle(btn);
      return {
        text: btn.innerText.slice(0, 30),
        backgroundColor: style.backgroundColor,
        color: style.color,
        boxShadow: style.boxShadow,
        padding: style.padding,
      };
    });
  });
  return buttons;
}

async function runAudit() {
  const browser = await chromium.launch();
  const results = {
    colorValidation: {},
    textContrast: {},
    buttonStyles: {},
    responsiveBreakpoints: {},
    issues: [],
  };

  for (const [breakpointKey, viewport] of Object.entries(BREAKPOINTS)) {
    console.log(`\n========================================`);
    console.log(`Testing: ${viewport.name}`);
    console.log(`========================================\n`);

    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: 1,
    });

    const page = await context.newPage();

    results.responsiveBreakpoints[breakpointKey] = {
      viewport,
      pages: {},
    };

    for (const pageTest of PAGES_TO_TEST) {
      try {
        console.log(`Testing: ${pageTest.name}`);

        // Navigate to page
        await page.goto(`${BASE_URL}${pageTest.path}`, { waitUntil: 'networkidle' });

        // Wait for content to load
        try {
          await page.waitForSelector(pageTest.waitFor, { timeout: 5000 });
        } catch (e) {
          console.warn(`  Warning: Expected selector not found: ${pageTest.waitFor}`);
        }

        // Validate colors
        const colors = await validateColors(page, viewport);
        console.log(`  Colors: BG=${colors.backgroundColor}, Text=${colors.color}`);

        // Check heading hierarchy
        const headings = await page.evaluate(() => {
          const h1 = document.querySelector('h1');
          const h2 = document.querySelector('h2');
          const h3 = document.querySelector('h3');
          return {
            h1: h1 ? { text: h1.innerText.slice(0, 50), size: window.getComputedStyle(h1).fontSize } : null,
            h2: h2 ? { text: h2.innerText.slice(0, 50), size: window.getComputedStyle(h2).fontSize } : null,
            h3: h3 ? { text: h3.innerText.slice(0, 50), size: window.getComputedStyle(h3).fontSize } : null,
          };
        });

        if (headings.h1) console.log(`  H1 Size: ${headings.h1.size}`);
        if (headings.h2) console.log(`  H2 Size: ${headings.h2.size}`);

        // Check contrast
        const bodyContrast = await checkContrast(page, 'body');
        if (bodyContrast) console.log(`  Body contrast: color=${bodyContrast.color}`);

        // Check button styles
        const buttons = await checkButtonStyles(page);
        if (buttons.length > 0) {
          console.log(`  Buttons found: ${buttons.length}`);
          buttons.forEach((btn, idx) => {
            console.log(`    Button ${idx + 1}: "${btn.text}" - BG: ${btn.backgroundColor}`);
          });
        }

        // Take screenshot
        const screenshotName = `${pageTest.name}-${breakpointKey}`;
        const screenshotPath = path.join(SCREENSHOTS_DIR, `${screenshotName}.png`);
        await page.screenshot({
          path: screenshotPath,
          fullPage: false,
        });
        console.log(`  ✓ Screenshot: ${screenshotName}.png`);

        results.responsiveBreakpoints[breakpointKey].pages[pageTest.name] = {
          colors,
          headings,
          buttons: buttons.length,
        };
      } catch (error) {
        console.error(`  ✗ Error testing ${pageTest.name}: ${error.message}`);
        results.issues.push({
          viewport: breakpointKey,
          page: pageTest.name,
          error: error.message,
        });
      }
    }

    await context.close();
  }

  await browser.close();

  // Save results
  const reportPath = path.join(SCREENSHOTS_DIR, 'audit-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`\n✓ Audit report saved: ${reportPath}`);
  console.log(`✓ Screenshots saved to: ${SCREENSHOTS_DIR}`);
}

runAudit().catch(console.error);
