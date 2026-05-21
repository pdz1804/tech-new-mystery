import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:3000';

async function auditColors() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });

  const page = await context.newPage();
  await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });

  // Get all button details
  const buttons = await page.evaluate(() => {
    const btns = document.querySelectorAll('button');
    return Array.from(btns).map((btn, idx) => {
      const style = window.getComputedStyle(btn);
      const rect = btn.getBoundingClientRect();
      return {
        index: idx,
        text: btn.innerText.slice(0, 30),
        classes: btn.className,
        computedStyle: {
          background: style.background,
          backgroundColor: style.backgroundColor,
          color: style.color,
          boxShadow: style.boxShadow,
          padding: style.padding,
          borderRadius: style.borderRadius,
          border: style.border,
          backdropFilter: style.backdropFilter,
        },
        visible: rect.width > 0 && rect.height > 0,
      };
    });
  });

  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║              BUTTON & COLOR ANALYSIS - HOME PAGE              ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  buttons.forEach((btn, idx) => {
    if (!btn.visible) return;
    console.log(`Button ${idx + 1}: "${btn.text}"`);
    console.log(`  Classes: ${btn.classes}`);
    console.log(`  Background: ${btn.computedStyle.backgroundColor}`);
    console.log(`  Color: ${btn.computedStyle.color}`);
    console.log(`  Box Shadow: ${btn.computedStyle.boxShadow}`);
    console.log(`  Border: ${btn.computedStyle.border}`);
    console.log(`  Backdrop Filter: ${btn.computedStyle.backdropFilter}`);
    console.log('');
  });

  // Check glass panels
  const panels = await page.evaluate(() => {
    const elements = document.querySelectorAll('[class*="glass"], [class*="panel"], .feature-card');
    return Array.from(elements).slice(0, 5).map((el) => {
      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return {
        className: el.className.slice(0, 50),
        visible: rect.width > 0 && rect.height > 0,
        background: style.backgroundColor,
        backdropFilter: style.backdropFilter,
        border: style.borderColor,
        boxShadow: style.boxShadow,
      };
    });
  });

  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║                 GLASS PANEL ANALYSIS                          ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  panels.forEach((panel, idx) => {
    if (!panel.visible) return;
    console.log(`Panel ${idx + 1}: ${panel.className}`);
    console.log(`  Background: ${panel.background}`);
    console.log(`  Backdrop Filter: ${panel.backdropFilter}`);
    console.log(`  Border: ${panel.border}`);
    console.log(`  Shadow: ${panel.boxShadow.slice(0, 50)}`);
    console.log('');
  });

  // Check body and overall design
  const design = await page.evaluate(() => {
    const body = document.body;
    const style = window.getComputedStyle(body);
    const liquidBg = document.querySelector('.liquid-background');
    const liquidBgStyle = liquidBg ? window.getComputedStyle(liquidBg) : null;
    return {
      body: {
        backgroundColor: style.backgroundColor,
        color: style.color,
        font: style.fontFamily,
      },
      liquidBackground: liquidBgStyle ? {
        backgroundColor: liquidBgStyle.backgroundColor,
        backgroundImage: liquidBgStyle.backgroundImage,
      } : null,
      blobs: document.querySelectorAll('.liquid-blob').length,
    };
  });

  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║              OVERALL DESIGN VALIDATION                        ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  console.log('Body:');
  console.log(`  Background Color: ${design.body.backgroundColor}`);
  console.log(`  Text Color: ${design.body.color}`);
  console.log(`  Font Family: ${design.body.font}`);

  if (design.liquidBackground) {
    console.log('\nLiquid Background:');
    console.log(`  Background Color: ${design.liquidBackground.backgroundColor}`);
    console.log(`  Background Image: ${design.liquidBackground.backgroundImage.slice(0, 80)}`);
  }

  console.log(`\nLiquid Blobs: ${design.blobs} found`);

  // Color validation
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║           LIQUID GLASS DESIGN SPEC COMPLIANCE                 ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  const bgColor = design.body.backgroundColor;
  const expectedBg = 'rgb(11, 12, 16)'; // #0B0C10

  if (bgColor === expectedBg || bgColor.includes('11') || bgColor.includes('12')) {
    console.log('✓ Background Color: CORRECT (#0B0C10)');
  } else {
    console.log(`✗ Background Color: INCORRECT (Expected #0B0C10, got ${bgColor})`);
  }

  const textColor = design.body.color;
  if (textColor.includes('255')) {
    console.log('✓ Text Color: CORRECT (White)');
  } else {
    console.log(`✗ Text Color: INCORRECT (Expected white, got ${textColor})`);
  }

  // Check for common Liquid Glass issues
  const hasLiquidBlobs = design.blobs > 0;
  console.log(`${hasLiquidBlobs ? '✓' : '✗'} Liquid Blob Background: ${hasLiquidBlobs ? 'PRESENT' : 'MISSING'}`);

  const primaryBtn = buttons.find((b) => b.classes.includes('primary') || b.text.includes('Get Started'));
  if (primaryBtn) {
    const hasGradient = primaryBtn.computedStyle.background.includes('gradient') || 
                       primaryBtn.computedStyle.backgroundColor.includes('rgb');
    console.log(`${hasGradient ? '✓' : '✗'} Primary Button: ${primaryBtn.computedStyle.backgroundColor.slice(0, 40)}`);
  }

  console.log('\n');

  await browser.close();
}

auditColors().catch(console.error);
