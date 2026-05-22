'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Menu,
  X,
  Bell,
  LogOut,
  User,
  Bookmark,
  Home,
  Compass,
  List,
  CheckSquare,
  Users,
} from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import GlassContainer from '@/components/ui/GlassContainer';
import SquircleButton from '@/components/ui/SquircleButton';

export function Header() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery)}`);
      setSearchQuery('');
      setIsMenuOpen(false);
    }
  };

  const handleLogout = () => {
    clearAuth();
    router.push('/login');
  };

  // Show public header if not authenticated
  if (!isAuthenticated) {
    return (
      <header className="glass-base fixed left-1/2 top-3 z-50 w-[calc(100%-2rem)] max-w-[1440px] -translate-x-1/2 rounded-[28px] border border-black/10 border-t-white/70 shadow-[0_20px_40px_-10px_rgba(0,0,0,0.18)] backdrop-blur-3xl">
        <nav className="mx-auto max-w-7xl px-4 py-3 md:py-4">
          <div className="flex items-center justify-between">
            <Link
              href="/"
              className="inline-flex items-center gap-2.5 transition-all duration-200 hover:opacity-80 flex-shrink-0"
              aria-label="Tech News home"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white font-bold text-sm">
                T
              </div>
              <span className="hidden sm:inline text-lg font-bold text-black">
                Tech News
              </span>
            </Link>

            <div className="flex items-center gap-4 flex-shrink-0">
              <SquircleButton
                variant="tertiary"
                size="sm"
                onClick={() => { window.location.href = '/login'; }}
              >
                Sign In
              </SquircleButton>
              <SquircleButton
                variant="primary"
                size="sm"
                onClick={() => { window.location.href = '/register'; }}
              >
                Get Started
              </SquircleButton>
            </div>
          </div>
        </nav>
      </header>
    );
  }

  return (
    <header className="glass-base fixed left-1/2 top-3 z-50 w-[calc(100%-2rem)] max-w-[1440px] -translate-x-1/2 rounded-[28px] border border-black/10 border-t-white/70 shadow-[0_20px_40px_-10px_rgba(0,0,0,0.18)] backdrop-blur-3xl">
      <nav className="mx-auto max-w-7xl px-4 py-3 md:py-4">
        {/* Desktop Navigation */}
        <div className="hidden md:flex md:flex-col md:gap-3">
          {/* Top Bar */}
          <div className="flex items-center justify-between gap-6">
            {/* Logo */}
            <Link
              href="/"
              className="inline-flex items-center gap-2.5 transition-all duration-200 hover:opacity-80 flex-shrink-0"
              aria-label="Tech News home"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white font-bold text-sm">
                T
              </div>
              <span className="hidden sm:inline text-lg font-bold text-black">
                Tech News
              </span>
            </Link>

            {/* Search Bar */}
            <form onSubmit={handleSearch} className="hidden sm:flex flex-1 max-w-sm lg:max-w-md px-4 lg:px-6">
              <div className="w-full relative group">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-black/30 group-focus-within:text-blue-600 transition-colors duration-micro flex-shrink-0 pointer-events-none" size={18} aria-hidden="true" />
                <input
                  type="search"
                  placeholder="Search articles..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="input-glass pl-10"
                  aria-label="Search articles"
                  autoComplete="off"
                />
              </div>
            </form>

            {/* Right Actions */}
            <div className="flex items-center gap-4 flex-shrink-0">
              <button
                type="button"
                aria-label="Notifications (no new messages)"
                className="relative p-2 text-black/60 hover:text-black hover:bg-black/5 rounded-lg transition-all duration-100"
              >
                <Bell size={20} aria-hidden="true" />
                <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-red-500" aria-hidden="true" />
              </button>

              {/* User Menu */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  aria-label={`User menu for ${user?.username}`}
                  aria-expanded={showUserMenu}
                  aria-haspopup="menu"
                  className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-black/5 transition-all duration-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500/50"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-600 text-white text-xs font-bold flex-shrink-0">
                    {user?.username?.charAt(0).toUpperCase()}
                  </div>
                  <span className="hidden lg:inline text-sm font-medium text-black">
                    {user?.username}
                  </span>
                </button>

                <AnimatePresence>
                  {showUserMenu && (
                    <motion.div
                      initial={{ opacity: 0, y: -8, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -8, scale: 0.95 }}
                      transition={{ duration: 0.15 }}
                      role="menu"
                      className="absolute right-0 mt-2 w-48 rounded-lg overflow-hidden z-50"
                    >
                      <GlassContainer variant="elevated" className="w-full">
                        <Link
                          href="/profile"
                          className="flex items-center gap-3 px-4 py-2.5 text-sm text-black/60 hover:bg-black/5 hover:text-black transition-colors duration-150 border-b border-black/8 focus:outline-none focus:bg-black/5"
                          onClick={() => setShowUserMenu(false)}
                          role="menuitem"
                        >
                          <User size={16} aria-hidden="true" />
                          My Profile
                        </Link>
                        <Link
                          href="/profile?tab=saved"
                          className="flex items-center gap-3 px-4 py-2.5 text-sm text-black/60 hover:bg-black/5 hover:text-black transition-colors duration-150 border-b border-black/8 focus:outline-none focus:bg-black/5"
                          onClick={() => setShowUserMenu(false)}
                          role="menuitem"
                        >
                          <Bookmark size={16} aria-hidden="true" />
                          Saved Articles
                        </Link>
                        <button
                          onClick={() => {
                            setShowUserMenu(false);
                            handleLogout();
                          }}
                          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/30 hover:text-red-200 transition-colors duration-150 focus:outline-none focus:bg-red-500/30 rounded-b-lg"
                          role="menuitem"
                        >
                          <LogOut size={16} aria-hidden="true" />
                          Logout
                        </button>
                      </GlassContainer>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex gap-8 border-t border-black/8 pt-3 -mx-4 px-4" aria-label="Main navigation">
            <NavLink href="/" icon={<Home size={18} />} label="Home" />
            <NavLink href="/articles" icon={<List size={18} />} label="Articles" />
            <NavLink href="/search" icon={<Compass size={18} />} label="Browse" />
            <NavLink href="/profile?tab=saved" icon={<Bookmark size={18} />} label="Saved" />
            {user?.is_admin && (
              <>
                <NavLink href="/admin/queue" icon={<CheckSquare size={18} />} label="Queue" />
                <NavLink href="/admin/users" icon={<Users size={18} />} label="Users" />
              </>
            )}
          </nav>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden space-y-3">
          {/* Top Bar */}
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2" aria-label="Tech News home">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white font-bold text-sm">
                T
              </div>
              <span className="text-base font-bold text-black">Tech News</span>
            </Link>

            <button
              type="button"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              aria-label="Toggle navigation menu"
              aria-expanded={isMenuOpen}
              aria-controls="mobile-menu"
              className="p-2 text-black/60 hover:bg-black/5 rounded-lg transition-all duration-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            >
              {isMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>

          {/* Mobile Search Bar */}
          <form onSubmit={handleSearch} className="w-full">
            <div className="relative group">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-black/45 group-focus-within:text-black transition-colors duration-150 flex-shrink-0 pointer-events-none" size={18} aria-hidden="true" />
              <input
                type="search"
                placeholder="Search articles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-glass pl-10"
                aria-label="Search articles"
                autoComplete="off"
              />
            </div>
          </form>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {isMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              id="mobile-menu"
              className="md:hidden mt-3 border-t border-black/8 pt-3"
            >
              <div className="space-y-1">
                <MobileNavLink href="/" icon={<Home size={18} />} label="Home" />
                <MobileNavLink href="/articles" icon={<List size={18} />} label="Articles" />
                <MobileNavLink href="/search" icon={<Compass size={18} />} label="Browse" />
                <MobileNavLink href="/profile?tab=saved" icon={<Bookmark size={18} />} label="Saved" />
                {user?.is_admin && (
                  <>
                    <MobileNavLink href="/admin/queue" icon={<CheckSquare size={18} />} label="Queue" />
                    <MobileNavLink href="/admin/users" icon={<Users size={18} />} label="Users" />
                  </>
                )}
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-red-600 hover:bg-red-50/50 rounded-lg transition-colors duration-150"
                >
                  <LogOut size={18} aria-hidden="true" />
                  Logout
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>
    </header>
  );
}

function NavLink({
  href,
  icon,
  label,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-2 text-sm font-medium text-black/60 transition-colors duration-150 hover:text-black border-b-2 border-transparent hover:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded px-2 py-1"
    >
      {icon}
      {label}
    </Link>
  );
}

function MobileNavLink({
  href,
  icon,
  label,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 px-3 py-2.5 text-sm font-medium text-black/60 rounded-lg hover:bg-black/5 hover:text-black transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      {icon}
      {label}
    </Link>
  );
}
