'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { LogIn, Mail, Lock, ChevronRight } from 'lucide-react';
import { useLogin } from '@/hooks/useAuth';
import SquircleButton from '@/components/ui/SquircleButton';
import GlassContainer from '@/components/ui/GlassContainer';

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
      className="min-h-screen flex items-center justify-center bg-white px-4 py-12"
    >
      <motion.div variants={containerVariants} className="relative w-full max-w-md">
        {/* Header Section */}
        <div className="mb-8 text-center">
          <motion.div
            variants={containerVariants}
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 mb-4"
          >
            <LogIn className="w-8 h-8 text-white" />
          </motion.div>
          <motion.h1 variants={containerVariants} className="text-3xl font-bold text-slate-900">
            Welcome Back
          </motion.h1>
          <motion.p variants={containerVariants} className="mt-2 text-slate-600 text-base">
            Sign in to your account to continue
          </motion.p>
        </div>

        {/* Clean Card Container */}
        <motion.div variants={containerVariants}>
          <GlassContainer variant="elevated" className="floating-card p-8">
            {/* Error Alert */}
            {loginMutation.error && (
              <motion.div
                variants={containerVariants}
                role="alert"
                aria-live="polite"
                aria-atomic="true"
                className="mb-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-red-700 text-sm"
              >
                {errorMessage}
              </motion.div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-5" aria-label="Sign in form">
              {/* Username Field */}
              <motion.div variants={containerVariants}>
                <label htmlFor="username" className="block text-sm font-medium text-slate-900 mb-2">
                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-blue-600" aria-hidden="true" />
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
                  className="input-base"
                />
              </motion.div>

              {/* Password Field */}
              <motion.div variants={containerVariants}>
                <label htmlFor="password" className="block text-sm font-medium text-slate-900 mb-2">
                  <div className="flex items-center gap-2">
                    <Lock className="w-4 h-4 text-blue-600" aria-hidden="true" />
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
                  className="input-base"
                />
              </motion.div>

              {/* Remember Me & Forgot Password */}
              <motion.div
                variants={containerVariants}
                className="flex items-center justify-between text-sm"
              >
                <label htmlFor="remember-me" className="flex items-center gap-2 text-slate-700 cursor-pointer hover:text-slate-900 transition">
                  <input
                    id="remember-me"
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded w-4 h-4 border border-slate-300 bg-white checked:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600 cursor-pointer accent-blue-600"
                  />
                  Remember me
                </label>
                <Link
                  href="/forgot-password"
                  className="text-blue-600 hover:text-blue-700 transition focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 rounded px-2 py-1"
                >
                  Forgot password?
                </Link>
              </motion.div>

              {/* Sign In Button */}
              <motion.div variants={containerVariants}>
                <SquircleButton
                  type="submit"
                  disabled={loginMutation.isPending}
                  variant="primary"
                  size="lg"
                  className="w-full justify-center"
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
                </SquircleButton>
              </motion.div>
            </form>

            {/* Sign Up Link */}
            <motion.div variants={containerVariants} className="mt-6 pt-6 border-t border-slate-200">
              <p className="text-center text-sm text-slate-700">
                Don&apos;t have an account?{' '}
                <Link
                  href="/register"
                  className="font-semibold text-blue-600 hover:text-blue-700 transition inline-flex items-center gap-1"
                >
                  Create one now
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </p>
            </motion.div>
          </GlassContainer>
        </motion.div>

        {/* Footer Text */}
        <motion.p variants={containerVariants} className="mt-6 text-center text-xs text-slate-600">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </motion.p>
      </motion.div>
    </motion.div>
  );
}
