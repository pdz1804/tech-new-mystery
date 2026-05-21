'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { LogIn, Mail, Lock, ChevronRight } from 'lucide-react';
import { useLogin } from '@/hooks/useAuth';

const containerVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const loginMutation = useLogin();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loginMutation.mutate({ username, password });
  };

  const errorMessage =
    loginMutation.error instanceof Error
      ? loginMutation.error.message
      : 'Login failed. Please try again.';

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="auth-photo-shell"
    >
      <picture>
        <source media="(max-width: 768px)" srcSet="/img/background-mobile-02.jpg" />
        <source media="(min-width: 769px)" srcSet="/img/background-web-02.jpg" />
        <img src="/img/background-web-02.jpg" alt="Tech workspace background" />
      </picture>

      <motion.div variants={containerVariants} className="auth-panel">
        {/* Header Section */}
        <div className="mb-7 text-center">
          <motion.div
            variants={containerVariants}
            className="auth-icon mb-4"
          >
            <LogIn className="h-7 w-7" />
          </motion.div>
          <motion.h1 variants={containerVariants} className="text-3xl font-bold text-black">
            Welcome Back
          </motion.h1>
          <motion.p variants={containerVariants} className="mt-2 text-base text-black/62">
            Sign in to your account to continue
          </motion.p>
        </div>

            {/* Error Alert */}
            {loginMutation.error && (
              <motion.div
                variants={containerVariants}
                role="alert"
                aria-live="polite"
                aria-atomic="true"
                className="mb-6 rounded-2xl border border-red-500/20 bg-red-50/80 px-4 py-3 text-sm font-medium text-red-700"
              >
                {errorMessage}
              </motion.div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-5" aria-label="Sign in form">
              {/* Username Field */}
              <motion.div variants={containerVariants}>
                <label htmlFor="username" className="mb-2 block text-sm font-semibold text-black/82">
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4 text-blue-600" aria-hidden="true" />
                    Username
                  </div>
                </label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your username"
                  required
                  className="auth-field"
                />
              </motion.div>

              {/* Password Field */}
              <motion.div variants={containerVariants}>
                <label htmlFor="password" className="mb-2 block text-sm font-semibold text-black/82">
                  <div className="flex items-center gap-2">
                    <Lock className="h-4 w-4 text-blue-600" aria-hidden="true" />
                    Password
                  </div>
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  className="auth-field"
                />
              </motion.div>

              {/* Remember Me & Forgot Password */}
              <motion.div
                variants={containerVariants}
                className="flex items-center justify-between text-sm"
              >
                <label htmlFor="remember-me" className="flex cursor-pointer items-center gap-2 text-black/62 transition hover:text-black">
                  <input
                    id="remember-me"
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="h-4 w-4 cursor-pointer rounded border border-black/20 bg-white/70 accent-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                  Remember me
                </label>
                <Link
                  href="/forgot-password"
                  className="rounded px-2 py-1 font-medium text-blue-700 transition hover:text-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  Forgot password?
                </Link>
              </motion.div>

              {/* Sign In Button */}
              <motion.div variants={containerVariants}>
                <button
                  type="submit"
                  disabled={loginMutation.isPending}
                  className="btn-liquid primary flex w-full items-center justify-center gap-2"
                >
                  {loginMutation.isPending ? (
                    <>
                      <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" role="status" aria-label="Signing in" />
                      Signing in...
                    </>
                  ) : (
                    <>
                      Sign In
                      <ChevronRight className="w-4 h-4" aria-hidden="true" />
                    </>
                  )}
                </button>
              </motion.div>
            </form>

            {/* Sign Up Link */}
            <motion.div variants={containerVariants} className="auth-divider mt-6 border-t pt-6">
              <p className="text-center text-sm text-black/62">
                Don&apos;t have an account?{' '}
                <Link
                  href="/register"
                  className="inline-flex items-center gap-1 font-semibold text-blue-700 transition hover:text-blue-900"
                >
                  Create one now
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </p>
            </motion.div>

        {/* Footer Text */}
        <motion.p variants={containerVariants} className="mt-5 text-center text-xs text-black/48">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </motion.p>
      </motion.div>
    </motion.div>
  );
}
