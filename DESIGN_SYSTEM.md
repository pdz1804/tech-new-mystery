# Tech News Mystery - Design System & Feature Implementation Guide

## Overview

This document describes the complete redesign and feature enhancements implemented across three major phases:

1. **Phase 1: Dynamic Filters** - Article filters now calculate from actual database content
2. **Phase 2: Queue Search Parameters** - Admin search buttons trigger yesterday's tech news
3. **Phase 3: Apple Design System** - Modern Liquid Glass aesthetic with spatial depth

---

## Phase 1: Dynamic Filter Implementation

### ✅ What Was Implemented

Dynamic filters replace hardcoded category lists with real-time counts from the database.

**Backend Changes:**
- **New Endpoint:** `GET /v1/articles/filters`
- **File:** `backend/app/api/v1/articles/router.py`
- **Returns:** Category and source counts aggregated from all articles
- **Caching:** 5-minute cache (React Query staleTime)

**Sample Response:**
```json
{
  "success": true,
  "data": {
    "categories": [
      { "name": "AI", "count": 12 },
      { "name": "Web Development", "count": 8 },
      { "name": "DevOps", "count": 5 }
    ],
    "sources": [
      { "name": "TechCrunch", "count": 3 },
      { "name": "The Verge", "count": 2 }
    ]
  }
}
```

**Frontend Changes:**
- **New Hook:** `frontend/src/hooks/useFilterMetadata.ts`
- **Updated Pages:**
  - `/articles/page.tsx` - Dynamic filter pills with counts
  - `/search/page.tsx` - Dynamic category filter badges
- **Features:**
  - Loading skeletons while fetching
  - Disabled filters for zero-count categories
  - Count badges show (n) beside category name

### How to Use

```typescript
import { useFilterMetadata } from '@/hooks/useFilterMetadata';

function MyComponent() {
  const { data: filterData, isLoading } = useFilterMetadata();

  return (
    <div>
      {filterData?.data?.categories.map((cat) => (
        <span key={cat.name}>
          {cat.name} ({cat.count})
        </span>
      ))}
    </div>
  );
}
```

---

## Phase 2: Queue Search Parameters (Yesterday's Tech News)

### ✅ What Was Implemented

Admin queue buttons now search for yesterday's news using specific tech keywords.

**Backend Changes:**
- **Updated Endpoints:**
  - `POST /admin/tavily/trigger` - Now accepts `start_date` (YYYY-MM-DD)
  - `POST /admin/newsapi/trigger` - Now accepts `from_date` (YYYY-MM-DD)
- **Files Modified:**
  - `backend/app/api/v1/admin/router.py` (lines 494-547)
  - `backend/app/workers/tasks/tavily_tasks.py` - Added `start_date` parameter
  - `backend/app/workers/tasks/newsapi_tasks.py` - Added `from_date` parameter
- **Default Behavior:** If no date provided, defaults to yesterday

**Frontend Changes:**
- **File:** `frontend/src/app/admin/queue/page.tsx` (lines 120-130)
- **Functionality:**
  - Automatically calculates yesterday's date
  - Passes date to API endpoints
  - Shows loading indicator during search
  - Button labels updated to reflect "Yesterday's search"

### Example API Call

```bash
# Search Tavily for yesterday's articles
POST /api/v1/admin/tavily/trigger?start_date=2026-05-20

# Search NewsAPI for yesterday's articles
POST /api/v1/admin/newsapi/trigger?from_date=2026-05-20
```

### How to Use in Frontend

```typescript
const handleSearch = async (source: 'tavily' | 'newsapi') => {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const dateParam = yesterday.toISOString().split('T')[0];

  const endpoint = source === 'tavily' ? '/admin/tavily/trigger' : '/admin/newsapi/trigger';
  const params = new URLSearchParams();
  params.append(source === 'tavily' ? 'start_date' : 'from_date', dateParam);

  const response = await fetch(`${endpoint}?${params}`);
  // Handle response...
};
```

---

## Phase 3: Apple Design System

### 🎨 Design Foundations

The Apple Design System implements:

1. **Liquid Glass** - Frosted glass effect with backdrop blur
2. **Spatial Depth** - Cards float with realistic shadows
3. **Squircle Geometry** - Continuous curvature (18px radius)
4. **Vibrancy** - Colors adapt to content beneath glass
5. **8pt Grid** - All spacing in 8px increments
6. **Content-First** - UI fades, content is the hero

### CSS Design System

**File:** `frontend/src/styles/apple-design.css`

#### Color System

```css
/* Light Mode (default) */
--color-text-primary: #000000
--color-text-secondary: rgba(60, 60, 67, 0.6)
--color-bg-primary: #ffffff
--color-bg-secondary: #f5f5f7
--color-accent: #0a84ff (System Blue)

/* Dark Mode (prefers-color-scheme: dark) */
--color-text-primary: #ffffff
--color-text-secondary: rgba(235, 235, 245, 0.7)
--color-bg-primary: #000000
--color-bg-secondary: #1c1c1e
```

#### Glass Materials

```css
.glass-container {
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(25px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 18px;
}

.glass-container.elevated {
  box-shadow: 0 4px 16px rgba(0,0,0,0.12), 
              0 16px 48px rgba(0,0,0,0.20);
}

.glass-container.nested {
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(20px);
}
```

#### Spatial Depth Shadows

```css
--shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.08);
--shadow-md: 0 8px 24px rgba(0, 0, 0, 0.12);
--shadow-lg: 0 24px 48px rgba(0, 0, 0, 0.16);
--shadow-floating: [three-layer shadow for floating cards]
--shadow-elevated: [three-layer shadow for elevated modals]
```

#### 8pt Grid System

```css
--space-1: 8px
--space-2: 16px
--space-3: 24px
--space-4: 32px
--space-5: 40px
--space-6: 48px

/* Usage */
.gap-2 { gap: 16px; }
.p-3 { padding: 24px; }
```

### Components

#### GlassContainer

Frosted glass panel with backdrop blur and border.

```typescript
import GlassContainer from '@/components/ui/GlassContainer';

export default function MyComponent() {
  return (
    <GlassContainer variant="elevated">
      <h2>Glass Panel Content</h2>
      <p>This content is inside a glass container</p>
    </GlassContainer>
  );
}
```

**Props:**
- `variant`: 'default' | 'elevated' | 'nested'
- `blur`: Number (default 25px)
- `className`: Additional CSS classes
- `onClick`: Click handler

#### SquircleButton

Button with physics-based spring animations and continuous curvature.

```typescript
import SquircleButton from '@/components/ui/SquircleButton';

export default function MyComponent() {
  return (
    <>
      <SquircleButton variant="primary" onClick={() => alert('Clicked!')}>
        Save Changes
      </SquircleButton>

      <SquircleButton variant="secondary" size="lg">
        Cancel
      </SquircleButton>

      <SquircleButton variant="tertiary" disabled>
        Disabled Action
      </SquircleButton>
    </>
  );
}
```

**Props:**
- `variant`: 'primary' | 'secondary' | 'tertiary' (default: 'primary')
- `size`: 'sm' | 'md' | 'lg' (default: 'md')
- `disabled`: boolean (default: false)
- `onClick`: Click handler
- `type`: 'button' | 'submit' | 'reset'

### Implementing the Design System

#### 1. Use GlassContainer for Panels

```typescript
<GlassContainer variant="elevated" className="p-4">
  <h3>Filter Panel</h3>
  <div className="gap-2 flex">
    {/* Content */}
  </div>
</GlassContainer>
```

#### 2. Use SquircleButton for All Interactions

```typescript
<SquircleButton 
  variant="primary" 
  size="md"
  onClick={handleAction}
  aria-label="Perform action"
>
  Action Label
</SquircleButton>
```

#### 3. Apply Grid Spacing

```typescript
<div className="gap-3 flex flex-col">
  <div className="p-4">Spaced item 1</div>
  <div className="p-4">Spaced item 2</div>
</div>
```

#### 4. Add Floating Card Effects

```typescript
<div className="floating-card p-4 gap-2">
  <h4>Floating Content</h4>
  <p>This card hovers above the background</p>
</div>
```

### Tailwind Integration

The design system uses Tailwind CSS utility classes alongside the custom CSS:

```typescript
<div className="rounded-lg glass-container p-4 gap-2 flex flex-col shadow-lg">
  {/* Content with combined Tailwind and Apple Design utilities */}
</div>
```

---

## Migration Guide: Updating Existing Pages

To migrate an existing page to the Apple Design System:

### Step 1: Import Components
```typescript
import GlassContainer from '@/components/ui/GlassContainer';
import SquircleButton from '@/components/ui/SquircleButton';
```

### Step 2: Replace Card Containers
```typescript
// Before
<div className="bg-white p-4 rounded-lg shadow-md border border-gray-200">

// After
<GlassContainer variant="elevated" className="p-4">
```

### Step 3: Replace Buttons
```typescript
// Before
<button className="bg-blue-600 text-white px-4 py-2 rounded-lg">

// After
<SquircleButton variant="primary">
```

### Step 4: Apply Grid Spacing
```typescript
// Before
<div className="space-y-4">

// After
<div className="gap-4 flex flex-col">
```

### Step 5: Update Shadows
```typescript
// Before
className="shadow-lg"

// After
className="floating-card"  // or .elevated for modals
```

---

## Testing Checklist

### Phase 1: Dynamic Filters
- [ ] Visit `/articles` - filters load with counts
- [ ] Visit `/search` - category pills show counts
- [ ] Zero-count categories are disabled
- [ ] Filter metadata updates after creating article
- [ ] Mobile filters display correctly

### Phase 2: Queue Search Parameters
- [ ] Click Tavily button - searches yesterday's news
- [ ] Click NewsAPI button - searches yesterday's news
- [ ] Manual date override works via API
- [ ] Button shows loading indicator during search
- [ ] Queue items populate after search completes

### Phase 3: Apple Design System
- [ ] GlassContainer components render correctly
- [ ] Backdrop blur is visible
- [ ] SquircleButton animations are smooth
- [ ] Rounded corners appear as continuous curves
- [ ] Shadows create depth effect
- [ ] Text is readable over glass backgrounds
- [ ] Mobile responsiveness maintained
- [ ] Dark mode colors correct (if implemented)

---

## File Reference

### Backend Files
```
backend/
├── app/
│   ├── api/v1/
│   │   ├── articles/router.py (NEW /filters endpoint)
│   │   └── admin/router.py (Updated trigger endpoints)
│   ├── repositories/
│   │   └── article_repository.py (NEW get_filter_metadata method)
│   └── workers/tasks/
│       ├── tavily_tasks.py (Added start_date parameter)
│       └── newsapi_tasks.py (Added from_date parameter)
```

### Frontend Files
```
frontend/src/
├── styles/
│   └── apple-design.css (NEW design system)
├── hooks/
│   └── useFilterMetadata.ts (NEW hook)
├── components/ui/
│   ├── GlassContainer.tsx (NEW component)
│   └── SquircleButton.tsx (NEW component)
├── app/
│   ├── articles/page.tsx (Updated with dynamic filters)
│   ├── search/page.tsx (Updated with dynamic filters)
│   └── admin/queue/page.tsx (Updated with date parameters)
└── app/
    └── layout.tsx (Imports apple-design.css)
```

---

## Future Enhancements

### Design System
- [ ] Complete page redesigns using GlassContainer & SquircleButton
- [ ] Dark mode toggle with persistent preference
- [ ] Additional color palettes (green, red, orange, etc.)
- [ ] Animation library for complex transitions
- [ ] Icon system with SF Symbols equivalents

### Features
- [ ] Filter persistence in URL (shareable filter links)
- [ ] Advanced search with date ranges
- [ ] Saved filter presets for admins
- [ ] Search result analytics and trending topics
- [ ] Category suggestions based on query

### Performance
- [ ] Server-side filter caching
- [ ] Incremental search results
- [ ] Optimistic UI updates
- [ ] Offline filter support

---

## Support & Questions

For questions about the design system or feature implementation:

1. Check `CLAUDE.md` for architectural guidelines
2. Review this document for component usage
3. Examine existing implementations in `/articles` and `/search` pages
4. Check commit history for detailed change logs

---

**Last Updated:** 2026-05-21
**Implemented By:** Claude Code
**Status:** ✅ Phase 1, 2, 3 Core Implementation Complete
