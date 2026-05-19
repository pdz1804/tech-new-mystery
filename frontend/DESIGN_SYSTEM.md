# Tech News Mystery - Modern Design System

**Updated:** May 19, 2026  
**Style:** Glassmorphism + Modern Gradient + Smooth Animation  
**Target:** Professional tech news blog with modern, engaging UX

---

## 1. Design Principles

### Core Values
- **Modern**: Glass effects, gradients, smooth animations
- **Content-First**: Typography and readability prioritized
- **Minimal**: No unnecessary decoration, every element serves a purpose
- **Accessible**: WCAG AA compliance, clear focus states, respects prefers-reduced-motion
- **Performant**: Smooth 60fps animations, no layout shift (CLS < 0.1)

---

## 2. Color Palette

### Primary Colors
| Name | Value | Usage |
|------|-------|-------|
| **Primary** | `#0066FF` | Links, primary CTAs, focus states |
| **Primary Dark** | `#0052CC` | Hover state, active navigation |
| **Primary Light** | `#E6F0FF` | Background tint, light hover |

### Semantic Colors
| Name | Value | Usage |
|------|-------|-------|
| **Success** | `#10B981` | Success states, positive actions |
| **Warning** | `#F59E0B` | Warnings, caution states |
| **Error** | `#EF4444` | Errors, destructive actions |
| **Info** | `#3B82F6` | Informational messages |

### Neutral Palette
| Level | Light | Dark | Usage |
|-------|-------|------|-------|
| **50** | `#F9FAFB` | `#030712` | Backgrounds, section dividers |
| **100** | `#F3F4F6` | `#0F172A` | Secondary backgrounds |
| **200** | `#E5E7EB` | `#1E293B` | Borders, dividers |
| **400** | `#9CA3AF` | `#94A3B8` | Secondary text, placeholders |
| **600** | `#4B5563` | `#64748B` | Primary text |
| **900** | `#111827` | `#F8FAFC` | Body text (light/dark mode) |

### Gradients
```
Primary Gradient: linear-gradient(135deg, #0066FF 0%, #0084FF 100%)
Accent Gradient: linear-gradient(135deg, #7C3AED 0%, #0066FF 100%)
Warm Gradient: linear-gradient(135deg, #FF6B35 0%, #F59E0B 100%)
```

---

## 3. Typography

### Font Stack
```
Headings: 'Geist Sans', system-ui, -apple-system, sans-serif
Body: 'Geist Sans', system-ui, -apple-system, sans-serif
Mono: 'Geist Mono', 'SF Mono', Monaco, monospace
```

### Type Scale
| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| **Display** | 48px | 700 | 1.2 | Hero titles |
| **Heading 1** | 32px | 700 | 1.3 | Page titles |
| **Heading 2** | 24px | 700 | 1.4 | Section heads |
| **Heading 3** | 20px | 600 | 1.4 | Subsections |
| **Body Large** | 18px | 400 | 1.6 | Article text |
| **Body** | 16px | 400 | 1.6 | Standard text |
| **Body Small** | 14px | 400 | 1.5 | Secondary text |
| **Label** | 12px | 500 | 1.4 | Tags, badges |
| **Caption** | 12px | 400 | 1.4 | Helper text |

### Contrast Requirements
- **Body text**: ≥4.5:1 against background (WCAG AA)
- **Secondary text**: ≥3:1 against background
- **Focus indicator**: 2px solid ring, 2:1 minimum contrast

---

## 4. Effects & Elevation

### Glassmorphism
```css
/* Glass Effect Base */
.glass-effect {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

/* Dark Mode Glass */
.dark .glass-effect {
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(71, 85, 105, 0.3);
}
```

### Shadow Scale
| Level | Usage |
|-------|-------|
| **xs** | `0 1px 2px rgba(0,0,0,0.05)` | Subtle elevation, hover states |
| **sm** | `0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)` | Cards, inputs |
| **md** | `0 4px 6px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06)` | Floating actions |
| **lg** | `0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)` | Modals |
| **xl** | `0 20px 25px rgba(0,0,0,0.1), 0 10px 10px rgba(0,0,0,0.04)` | Drawer |

### Border Radius
| Level | Value | Usage |
|-------|-------|-------|
| **None** | 0 | Inputs (optional), tables |
| **sm** | 4px | Badges, small buttons |
| **md** | 8px | Cards, buttons, inputs |
| **lg** | 12px | Large cards, modals |
| **xl** | 16px | Hero sections |
| **full** | 9999px | Avatars, round buttons |

---

## 5. Animation & Motion

### Duration & Easing
| Type | Duration | Easing | Usage |
|------|----------|--------|-------|
| **Micro** | 150ms | ease-out | Button press, icon change |
| **Short** | 200ms | ease-out | Fade, slide, scale |
| **Standard** | 300ms | ease-out | Card entrance, modal |
| **Long** | 400ms | ease-out | Page transitions |

### Easing Functions
```css
--ease-out: cubic-bezier(0.4, 0, 0.2, 1);
--ease-in: cubic-bezier(0.4, 0, 1, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
```

### Animation Patterns
| Pattern | Effect | Duration | Use Case |
|---------|--------|----------|----------|
| **Fade** | opacity: 0 → 1 | 200ms | Content reveal, page transition |
| **Slide Up** | transform: translateY(16px) + fade | 300ms | Card entrance, modal |
| **Scale** | transform: scale(0.95) + fade | 200ms | Button press, hover |
| **Float** | subtle y translation | infinite | Floating elements, hover |
| **Pulse** | opacity pulse | 2s | Loading states, new badges |

### Respects Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation: none !important;
    transition: none !important;
  }
}
```

---

## 6. Component Specifications

### Buttons
**States**: Default, Hover, Active, Disabled, Loading

**Primary Button**
```
Style: Solid gradient background
Color: Primary gradient (#0066FF → #0084FF)
Height: 44px (mobile), 40px (desktop)
Padding: 12px 24px
Border Radius: 8px
Font: 14px / 600 weight
Transition: 150ms ease-out
Hover: Brightness +10%, shadow-sm
Active: Scale 0.95
Disabled: Opacity 50%, cursor not-allowed
```

**Secondary Button**
```
Style: Glass effect outline
Border: 1px solid border-200
Background: transparent
Hover: Background fade to slate-50
Active: Border-color to primary
```

### Cards
```
Background: Glass effect OR solid white
Border: 1px solid border-200 OR transparent
Border Radius: 12px
Shadow: shadow-sm
Padding: 24px
Hover: 
  - Shadow: shadow-md
  - Transform: translateY(-2px)
  - Duration: 200ms ease-out
```

### Input Fields
```
Height: 44px (mobile), 40px (desktop)
Padding: 12px 16px
Border Radius: 8px
Border: 1px solid border-200
Background: slate-50
Font: 14px / 16px body
Focus:
  - Border: primary-500
  - Ring: 2px primary-500 with 20% opacity
  - Shadow: shadow-sm
Disabled: Opacity 50%, background-100
```

### Links
```
Color: primary-600
Text Decoration: underline
Hover: 
  - Color: primary-700
  - Underline: 2px
Visited: Color slate-600
Focus: Ring + outline
```

---

## 7. Layout & Spacing

### Spacing Scale
```
4px, 8px, 12px, 16px, 20px, 24px, 32px, 40px, 48px, 56px, 64px
```

### Container Widths
| Breakpoint | Width | Max Width |
|-----------|-------|-----------|
| **Mobile** | 100% | none |
| **Tablet (768px)** | 100% | 720px |
| **Desktop (1024px)** | 100% | 960px |
| **Large (1440px)** | 100% | 1200px |

### Responsive Breakpoints
```
sm: 640px   (small phones)
md: 768px   (tablets)
lg: 1024px  (laptops)
xl: 1280px  (desktops)
2xl: 1536px (large desktops)
```

### Mobile-First Approach
- **Default**: Mobile (375px)
- **Scale up to tablet** (768px)
- **Scale up to desktop** (1024px+)

---

## 8. Dark Mode

### Color Overrides
| Component | Light | Dark |
|-----------|-------|------|
| **Background** | slate-50 | slate-950 |
| **Surface** | white | slate-900 |
| **Text Primary** | slate-900 | slate-50 |
| **Text Secondary** | slate-600 | slate-400 |
| **Border** | slate-200 | slate-700 |
| **Glass** | rgba(255,255,255,0.7) | rgba(30,41,59,0.7) |

### Testing
- Test both modes independently
- Ensure contrast ≥4.5:1 in both modes
- Verify borders/dividers visible in both modes
- Test on actual device (not just browser simulation)

---

## 9. Accessibility Checklist

### Critical
- [ ] Color contrast ≥4.5:1 for body text
- [ ] Focus indicators visible on all interactive elements
- [ ] Keyboard navigation: Tab order logical
- [ ] Forms: Labels associated with inputs
- [ ] Images: Meaningful alt text
- [ ] Animations respect `prefers-reduced-motion`

### High Priority
- [ ] Focus ring width ≥2px, color contrast ≥2:1
- [ ] Touch targets ≥44px × 44px
- [ ] Link underlines or other non-color indicator
- [ ] Error messages near the error field
- [ ] ARIA labels for icon-only buttons

### Validation Tools
- axe DevTools (Chrome extension)
- WAVE (WebAIM)
- Lighthouse (Chrome DevTools)
- Manual testing with keyboard only
- Manual testing with screen reader (NVDA, JAWS)

---

## 10. Implementation Notes

### CSS Framework
- **Tailwind CSS** with custom theme extensions
- Custom utility classes for glass, gradients
- CSS variables for semantic colors

### Component Library
- **Lucide Icons**: All UI icons (consistent stroke width)
- **Framer Motion**: Smooth animations, gesture support
- **Radix UI**: Accessible primitives (buttons, selects, etc.)

### Performance Targets
- **First Contentful Paint (FCP)**: < 1.5s
- **Largest Contentful Paint (LCP)**: < 2.5s
- **Cumulative Layout Shift (CLS)**: < 0.1
- **Animation frame rate**: 60fps (no jank)

### Browser Support
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari 14+, Chrome 90+)

---

## 11. Anti-Patterns (Avoid)

- ❌ Using emojis as structural icons (use SVG/Lucide)
- ❌ Hardcoded colors in components (use design tokens)
- ❌ Animations > 400ms (feels sluggish)
- ❌ Excessive blur/glass (readability over aesthetics)
- ❌ Color as only indicator (add icons/text)
- ❌ Missing focus states (accessibility issue)
- ❌ Layout shift from images (use aspect-ratio)
- ❌ Icon + text hover underline changes width (CLS)
- ❌ Disabled state that looks clickable
- ❌ Animations that can't be interrupted

---

## 12. Design Tokens (Tailwind Config)

```javascript
// tailwind.config.js
{
  theme: {
    colors: {
      primary: {
        50: '#E6F0FF',
        500: '#0066FF',
        600: '#0052CC',
        700: '#0052CC',
      },
      success: '#10B981',
      error: '#EF4444',
      // ... more colors
    },
    spacing: {
      // 4px increments
      xs: '4px',
      sm: '8px',
      md: '16px',
      lg: '24px',
      xl: '32px',
    },
    animation: {
      fade: 'fadeIn 200ms ease-out',
      slideUp: 'slideUp 300ms ease-out',
      // ... more animations
    },
    backdropBlur: {
      glass: '8px',
    },
  }
}
```

---

**Last Updated**: May 19, 2026  
**Next Review**: June 1, 2026  
**Maintained By**: Design Team
