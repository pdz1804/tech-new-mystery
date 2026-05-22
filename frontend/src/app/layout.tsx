import type { Metadata } from 'next';
import { ReactNode } from 'react';
import { Inter, Merriweather } from 'next/font/google';
import { ReactQueryProvider } from '@/components/providers/ReactQueryProvider';
import { AuthHydration } from '@/components/providers/AuthHydration';
import { ScrollToTop } from '@/components/providers/ScrollToTop';
import { Header } from '@/components/layout/Header';
import '@/styles/globals.css';
import '@/styles/liquid-glass.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });
const merriweather = Merriweather({
  weight: ['400', '700'],
  subsets: ['latin'],
  variable: '--font-serif',
});

export const metadata: Metadata = {
  title: 'Tech News Mystery',
  description: 'AI-powered tech news aggregation platform',
  icons: {
    icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="%232563eb"/><text x="16" y="22" font-size="20" font-weight="bold" fill="white" text-anchor="middle" font-family="system-ui">T</text></svg>',
  },
};

interface RootLayoutProps {
  children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning className={`${inter.variable} ${merriweather.variable}`}>
      <body className="font-sans bg-[#FFFFFF] text-black overflow-x-hidden" suppressHydrationWarning>
        {/* Animated Liquid Background */}
        <div className="liquid-background">
          <div className="liquid-blob liquid-blob-1"></div>
          <div className="liquid-blob liquid-blob-2"></div>
          <div className="liquid-blob liquid-blob-3"></div>
        </div>

        <ReactQueryProvider>
          <AuthHydration />
          <ScrollToTop />
          {/* Skip to main content link for keyboard users */}
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:fixed focus:left-0 focus:top-0 focus:z-50 focus:bg-blue-600 focus:text-white focus:p-4"
          >
            Skip to main content
          </a>
          <Header />
          <main id="main-content">
            {children}
          </main>
        </ReactQueryProvider>
      </body>
    </html>
  );
}
