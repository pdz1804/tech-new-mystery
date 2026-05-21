import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:3000';

async function checkIssues() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });

  const page = await context.newPage();
  await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });

  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║          DETAILED ISSUE INVESTIGATION                         ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  // ISSUE 1: Typography Hierarchy
  console.log('ISSUE 1: Typography Hierarchy\n');
  const headings = await page.evaluate(() => {
    const all = [];
    document.querySelectorAll('h1, h2, h3, p').forEach((el) => {
      if (el.offsetParent) {
        const style = window.getComputedStyle(el);
        all.push({
          tag: el.tagName.toLowerCase(),
          size: parseInt(style.fontSize),
          text: el.textContent.slice(0, 40),
        });
      }
    });
    return all;
  });

  console.log('Found headings:');
  headings.forEach((h) => {
    console.log(`  ${h.tag.padEnd(4)}: ${h.size}px - "${h.text}"`);
  });

  const h1 = headings.find(h => h.tag === 'h1');
  const h2 = headings.find(h => h.tag === 'h2');
  const h3 = headings.find(h => h.tag === 'h3');
  const body = headings.find(h => h.tag === 'p');

  if (h1 && h2 && h3 && body) {
    if (h1.size > h2.size && h2.size > h3.size) {
      console.log('✓ Hierarchy correct: H1 > H2 > H3');
    } else {
      console.log('✗ Hierarchy issue detected!');
      if (h2 && h3 && h2.size <= h3.size) {
        console.log(`  Problem: H2 (${h2.size}px) should be larger than H3 (${h3.size}px)`);
      }
    }
  } else {
    console.log('Note: Not all heading levels present on home page');
    if (h1) console.log(`  H1: ${h1.size}px`);
    if (h2) console.log(`  H2: ${h2.size}px`);
    if (h3) console.log(`  H3: ${h3.size}px`);
    if (body) console.log(`  Body: ${body.size}px`);
  }

  // ISSUE 2: Hover States
  console.log('\n\nISSUE 2: Hover States\n');
  
  const hoverTest = await page.evaluate(() => {
    const card = document.querySelector('.feature-card');
    const btn = document.querySelector('button.btn-liquid.primary');

    return {
      card: card ? {
        transition: window.getComputedStyle(card).transition,
        transitionAll: window.getComputedStyle(card).transition.includes('all'),
      } : null,
      button: btn ? {
        transition: window.getComputedStyle(btn).transition,
        transitionAll: window.getComputedStyle(btn).transition.includes('all'),
      } : null,
    };
  });

  console.log('CSS Transitions defined:');
  if (hoverTest.card) {
    console.log(`  Card transition: ${hoverTest.card.transition}`);
    console.log(`  Includes "all": ${hoverTest.card.transitionAll ? '✓' : '✗'}`);
  }
  if (hoverTest.button) {
    console.log(`  Button transition: ${hoverTest.button.transition}`);
    console.log(`  Includes "all": ${hoverTest.button.transitionAll ? '✓' : '✗'}`);
  }

  // Test actual hover
  const card = await page.$('.feature-card');
  if (card) {
    await card.hover();
    const hoverStyle = await card.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        transform: style.transform,
        boxShadow: style.boxShadow,
      };
    });
    console.log('\nActual hover state (Card):');
    console.log(`  Transform: ${hoverStyle.transform}`);
    console.log(`  Box Shadow: ${hoverStyle.boxShadow.slice(0, 80)}`);
  }

  const btn = await page.$('button.btn-liquid.primary');
  if (btn) {
    await btn.hover();
    const hoverStyle = await btn.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        transform: style.transform,
        boxShadow: style.boxShadow,
      };
    });
    console.log('\nActual hover state (Button):');
    console.log(`  Transform: ${hoverStyle.transform}`);
    console.log(`  Box Shadow: ${hoverStyle.boxShadow.slice(0, 80)}`);
  }

  console.log('\n\nCSS DEFINITIONS CHECK:\n');

  // Read the CSS file directly
  console.log('Checking liquid-glass.css for hover definitions...\n');

  const cssFile = await import('fs');
  try {
    const css = cssFile.readFileSync('../src/styles/liquid-glass.css', 'utf-8');
    
    const cardHover = css.match(/\.feature-card:hover\s*\{[\s\S]*?\}/);
    const btnHover = css.match(/\.btn-liquid\.primary:hover\s*\{[\s\S]*?\}/);

    if (cardHover) {
      console.log('✓ Card hover definition found:');
      console.log(`  ${cardHover[0].slice(0, 150)}...`);
    } else {
      console.log('✗ Card hover definition NOT found');
    }

    if (btnHover) {
      console.log('\n✓ Button primary hover definition found:');
      console.log(`  ${btnHover[0].slice(0, 150)}...`);
    } else {
      console.log('\n✗ Button primary hover definition NOT found');
    }
  } catch (e) {
    console.log('Note: CSS file check requires file system access');
  }

  console.log('\n');
  await browser.close();
}

checkIssues().catch(console.error);
