import type { Metadata } from 'next';
import { ReactNode } from 'react';
import { Inter, Merriweather } from 'next/font/google';
import { ReactQueryProvider } from '@/components/providers/ReactQueryProvider';
import { AuthHydration } from '@/components/providers/AuthHydration';
import { ScrollToTop } from '@/components/providers/ScrollToTop';
import { Header } from '@/components/layout/Header';
import '@/styles/globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });
const merriweather = Merriweather({
  weight: ['400', '700'],
  subsets: ['latin'],
  variable: '--font-serif',
});

export const metadata: Metadata = {
  title: 'Tech News Mystery',
  description: 'AI-powered tech news aggregation platform',
};

interface RootLayoutProps {
  children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning style={{ ...inter.style.variables, ...merriweather.style.variables }}>
      <body className="font-sans bg-white" suppressHydrationWarning>
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
