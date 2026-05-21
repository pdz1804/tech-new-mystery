import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:3000';

async function auditAnimations() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });

  const page = await context.newPage();
  await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });

  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║         ANIMATION & PERFORMANCE AUDIT                         ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  // Check liquid blob animations
  const blobAnimations = await page.evaluate(() => {
    const blobs = document.querySelectorAll('.liquid-blob');
    return Array.from(blobs).map((blob) => {
      const style = window.getComputedStyle(blob);
      return {
        class: blob.className,
        animation: style.animation,
        willChange: style.willChange,
        filter: style.filter,
        opacity: style.opacity,
      };
    });
  });

  console.log('Liquid Blob Animations:');
  blobAnimations.forEach((blob, idx) => {
    console.log(`  Blob ${idx + 1}:`);
    console.log(`    Animation: ${blob.animation.slice(0, 60)}`);
    console.log(`    Will-change: ${blob.willChange}`);
    console.log(`    Filter: ${blob.filter.slice(0, 60)}`);
    console.log(`    Opacity: ${blob.opacity}`);
  });

  // Check button hover animations
  const hoverAnimations = await page.evaluate(() => {
    const buttons = document.querySelectorAll('button');
    return Array.from(buttons)
      .filter(b => b.offsetParent)
      .slice(0, 3)
      .map((btn) => {
        const style = window.getComputedStyle(btn);
        return {
          text: btn.innerText.slice(0, 20),
          transition: style.transition,
          transform: style.transform,
          cursor: style.cursor,
        };
      });
  });

  console.log('\nButton Transitions:');
  hoverAnimations.forEach((btn, idx) => {
    console.log(`  Button ${idx + 1} ("${btn.text}"):`);
    console.log(`    Transition: ${btn.transition.slice(0, 60)}`);
    console.log(`    Transform: ${btn.transform === 'none' ? 'none' : btn.transform}`);
    console.log(`    Cursor: ${btn.cursor}`);
  });

  // Simulate hover on primary button
  const primaryBtn = await page.$('button.btn-liquid.primary, button.btn-primary');
  if (primaryBtn) {
    console.log('\nHover State Test (Primary Button):');
    await primaryBtn.hover();
    
    const hoverStyle = await primaryBtn.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        boxShadow: style.boxShadow,
        transform: style.transform,
      };
    });

    console.log(`  Box Shadow: ${hoverStyle.boxShadow.slice(0, 80)}`);
    console.log(`  Transform: ${hoverStyle.transform === 'none' ? 'none' : hoverStyle.transform}`);
  }

  // Check card hover animations
  const cardHover = await page.evaluate(() => {
    const cards = document.querySelectorAll('.feature-card, [class*="card"]');
    return Array.from(cards).slice(0, 1).map((card) => {
      const style = window.getComputedStyle(card);
      return {
        className: card.className.slice(0, 40),
        transition: style.transition,
        transform: style.transform,
      };
    });
  });

  console.log('\nCard Animations:');
  cardHover.forEach((card, idx) => {
    console.log(`  Card ${idx + 1} (${card.className}):`);
    console.log(`    Transition: ${card.transition.slice(0, 80)}`);
    console.log(`    Transform: ${card.transform}`);
  });

  // Check for backdrop filter animations
  const backdropAnimations = await page.evaluate(() => {
    const els = document.querySelectorAll('[class*="glass"], [class*="modal"]');
    const backdropEls = Array.from(els).slice(0, 3);
    return backdropEls.map((el) => {
      const style = window.getComputedStyle(el);
      return {
        className: el.className.slice(0, 40),
        backdropFilter: style.backdropFilter,
        transition: style.transition,
      };
    });
  });

  console.log('\nBackdrop Filter Elements:');
  backdropAnimations.forEach((el, idx) => {
    console.log(`  Element ${idx + 1} (${el.className}):`);
    console.log(`    Backdrop Filter: ${el.backdropFilter}`);
    console.log(`    Transition: ${el.transition.slice(0, 60)}`);
  });

  // Performance metrics
  const metrics = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0];
    const paint = performance.getEntriesByType('paint');
    
    return {
      domReady: nav?.domContentLoadedEventEnd - nav?.domContentLoadedEventStart,
      loadComplete: nav?.loadEventEnd - nav?.loadEventStart,
      firstPaint: paint.find(p => p.name === 'first-paint')?.startTime,
      firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime,
    };
  });

  console.log('\nPerformance Metrics:');
  console.log(`  DOM Ready Time: ${metrics.domReady?.toFixed(0)}ms`);
  console.log(`  Load Complete: ${metrics.loadComplete?.toFixed(0)}ms`);
  console.log(`  First Paint: ${metrics.firstPaint?.toFixed(0)}ms`);
  console.log(`  First Contentful Paint: ${metrics.firstContentfulPaint?.toFixed(0)}ms`);

  // Check for reduced motion support
  const reducedMotion = await page.evaluate(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const css = Array.from(document.styleSheets)
      .map((sheet) => {
        try {
          return sheet.cssRules;
        } catch {
          return [];
        }
      })
      .flat()
      .filter((rule) => rule.media?.mediaText?.includes('prefers-reduced-motion'))
      .length;

    return {
      preferenceDetected: mediaQuery.matches,
      cssSupported: css > 0,
    };
  });

  console.log('\nAccessibility - Reduced Motion:');
  console.log(`  CSS media query support: ${reducedMotion.cssSupported ? '✓' : '✗'}`);

  console.log('\n');
  await browser.close();
}

auditAnimations().catch(console.error);
