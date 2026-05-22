/**
 * Color constants - Single source of truth for all design colors.
 * Extracted from REDESIGN_QUICK_REFERENCE.md
 */

export const colors = {
  // Brand colors
  brand: {
    primary: '#2563EB', // Vibrant Blue
    secondary: '#7C3AED', // Purple
  },

  // Text colors
  text: {
    primary: '#1F2937', // Dark Gray
    secondary: '#6B7280', // Medium Gray
    tertiary: '#9CA3AF', // Light Gray
  },

  // Status colors
  status: {
    success: '#10B981', // Green
    warning: '#F59E0B', // Amber
    error: '#EF4444', // Red
    info: '#3B82F6', // Light Blue
  },

  // Background colors
  background: {
    light: '#FFFFFF', // Pure White
    default: '#F9FAFB', // Off White
    secondary: '#F3F4F6', // Light Gray
    dark: '#111827', // Dark
  },

  // Utility colors for specific features
  featured: {
    bg: 'rgba(37, 99, 235, 0.1)', // Blue tint
    text: '#2563EB',
    border: '#2563EB',
    accentColor: '#2563EB',
  },

  trending: {
    bg: '#FFFBF0',
    text: '#F59E0B',
    border: '#FEE8C3',
    accentBorder: '#F59E0B',
  },

  // Glass effect colors
  glass: {
    light: {
      bg: 'rgba(255, 255, 255, 0.7)',
      border: 'rgba(255, 255, 255, 0.3)',
      shadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
    },
    dark: {
      bg: 'rgba(31, 41, 55, 0.05)',
      border: 'rgba(99, 102, 241, 0.1)',
      shadow: '0 4px 20px rgba(0, 0, 0, 0.12)',
    },
    heavy: {
      bg: 'rgba(255, 255, 255, 0.5)',
      border: 'rgba(255, 255, 255, 0.2)',
      shadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
    },
  },

  // Button shadows
  buttonShadows: {
    primary: '0 4px 12px rgba(37, 99, 235, 0.4)',
    secondary: '0 4px 12px rgba(124, 58, 237, 0.4)',
  },

  // Focus ring color
  focus: '#2563EB',
} as const;

export default colors;
