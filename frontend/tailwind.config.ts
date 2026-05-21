import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Primary Brand Colors (Modern Blue)
        primary: {
          50: '#E6F0FF',
          100: '#CCE1FF',
          500: '#0066FF',
          600: '#0052CC',
          700: '#003D99',
        },
        // Accent Colors
        accent: {
          purple: '#7C3AED',
          orange: '#FF6B35',
          amber: '#F59E0B',
        },
        // Semantic Colors
        success: '#10B981',
        warning: '#F59E0B',
        error: '#EF4444',
        info: '#3B82F6',
        // Text colors (improved contrast)
        text: {
          primary: '#111827',
          secondary: '#4B5563',
          tertiary: '#9CA3AF',
        },
        // Backgrounds
        bg: {
          light: '#FFFFFF',
          default: '#F9FAFB',
          secondary: '#F3F4F6',
          tertiary: '#E5E7EB',
          dark: '#111827',
        },
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', '"Helvetica Neue"', 'sans-serif'],
        mono: ['"Geist Mono"', '"SF Mono"', 'Monaco', 'monospace'],
      },
      fontSize: {
        'display': ['48px', { fontWeight: '700', lineHeight: '1.2' }],
        'h1': ['32px', { fontWeight: '700', lineHeight: '1.3' }],
        'h2': ['24px', { fontWeight: '700', lineHeight: '1.4' }],
        'h3': ['20px', { fontWeight: '600', lineHeight: '1.4' }],
        'body-lg': ['18px', { fontWeight: '400', lineHeight: '1.6' }],
        'body': ['16px', { fontWeight: '400', lineHeight: '1.6' }],
        'body-sm': ['14px', { fontWeight: '400', lineHeight: '1.5' }],
        'label': ['12px', { fontWeight: '500', lineHeight: '1.4' }],
        'caption': ['12px', { fontWeight: '400', lineHeight: '1.4' }],
      },
      backdropBlur: {
        glass: '8px',
        heavy: '12px',
        '3xl': '48px',
      },
      backgroundImage: {
        'gradient-primary': 'linear-gradient(135deg, #0066FF 0%, #0084FF 100%)',
        'gradient-accent': 'linear-gradient(135deg, #7C3AED 0%, #0066FF 100%)',
        'gradient-warm': 'linear-gradient(135deg, #FF6B35 0%, #F59E0B 100%)',
        'gradient-subtle': 'linear-gradient(to bottom, rgba(255,255,255,0.5), rgba(255,255,255,0))',
      },
      boxShadow: {
        // Elevation scale
        'sm': '0 1px 2px rgba(0, 0, 0, 0.05)',
        'md': '0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06)',
        'lg': '0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05)',
        'xl': '0 20px 25px rgba(0, 0, 0, 0.1), 0 10px 10px rgba(0, 0, 0, 0.04)',
        // Glass effects
        'glass': '0 8px 32px rgba(0, 0, 0, 0.1)',
        'glass-hover': '0 12px 48px rgba(0, 0, 0, 0.15)',
        // Special effects
        'glow-blue': '0 0 20px rgba(0, 102, 255, 0.3)',
        'glow-purple': '0 0 20px rgba(124, 58, 237, 0.3)',
      },
      animation: {
        // Entrance animations
        'fade-in': 'fadeIn 200ms ease-out forwards',
        'slide-up': 'slideUp 300ms ease-out forwards',
        'scale-in': 'scaleIn 200ms ease-out forwards',
        // Interactive animations
        'bounce-subtle': 'bounceSubtle 2s infinite',
        'pulse-glow': 'pulseGlow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        // Micro interactions
        'shake': 'shake 150ms ease-in-out',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(16px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        bounceSubtle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-4px)' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '25%': { transform: 'translateX(-2px)' },
          '75%': { transform: 'translateX(2px)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
      },
      transitionDuration: {
        micro: '150ms',
        short: '200ms',
        base: '300ms',
        long: '400ms',
      },
      transitionTimingFunction: {
        'ease-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'ease-in': 'cubic-bezier(0.4, 0, 1, 1)',
        'ease-in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [
    function ({ addComponents, theme }: any) {
      addComponents({
        // Glass components
        '.glass-base': {
          '@apply bg-white/70 backdrop-blur-[8px] border border-white/50': {},
        },
        '.glass-card': {
          '@apply bg-white/70 backdrop-blur-[8px] border border-white/50 rounded-xl shadow-glass': {},
        },
        '.glass-dark': {
          '@apply bg-slate-900/70 backdrop-blur-[8px] border border-slate-700/30': {},
        },

        // Input styles (improved)
        '.input-base': {
          '@apply h-10 w-full px-4 rounded-lg border border-slate-200 bg-slate-50 text-sm transition-all duration-150': {},
          '@apply placeholder-slate-500 focus:bg-white focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20': {},
          '@apply disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-slate-100': {},
        },

        // Button base styles
        '.btn-base': {
          '@apply inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150': {},
          '@apply h-10 px-4 text-sm': {},
          '@apply focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500': {},
          '@apply disabled:opacity-50 disabled:cursor-not-allowed': {},
        },
        '.btn-primary': {
          '@apply btn-base bg-gradient-to-r from-primary-500 to-primary-600 text-white': {},
          '@apply hover:shadow-lg active:scale-95': {},
        },
        '.btn-secondary': {
          '@apply btn-base bg-slate-100 text-slate-900 border border-slate-200': {},
          '@apply hover:bg-slate-200 active:scale-95': {},
        },
        '.btn-ghost': {
          '@apply btn-base text-slate-600 hover:bg-slate-100 active:scale-95': {},
        },

        // Card styles (enhanced)
        '.card': {
          '@apply glass-card p-6': {},
        },
        '.card-interactive': {
          '@apply card cursor-pointer transition-all duration-200': {},
          '@apply hover:shadow-glass-hover hover:-translate-y-1': {},
        },

        // Text utilities
        '.text-gradient': {
          '@apply bg-gradient-to-r from-primary-500 to-accent-purple bg-clip-text text-transparent': {},
        },
        '.text-balance': {
          'text-wrap': 'balance',
        },

        // Focus utilities
        '.focus-ring': {
          '@apply outline-none ring-2 ring-primary-500 ring-offset-2': {},
        },
        '.focus-visible-ring': {
          '@apply focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2': {},
        },

        // Transition utilities
        '.transition-smooth': {
          '@apply transition-all duration-short ease-out': {},
        },
        '.transition-smoother': {
          '@apply transition-all duration-base ease-out': {},
        },
      });
    },
  ],
};
export default config;
