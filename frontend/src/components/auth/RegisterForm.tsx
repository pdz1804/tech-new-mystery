'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { UserPlus, Mail, Lock, User, CheckCircle2, ChevronRight } from 'lucide-react';
import { useRegister } from '@/hooks/useAuth';

const containerVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export function RegisterForm() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const registerMutation = useRegister();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setPasswordError('Passwords do not match');
      return;
    }
    setPasswordError('');
    registerMutation.mutate({ username, email, password });
  };

  const errorMessage =
    registerMutation.error instanceof Error
      ? registerMutation.error.message
      : 'Registration failed. Please try again.';

  const passwordsMatch = password === confirmPassword && password.length > 0;
  const passwordStrengthOk = password.length >= 8;

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
        <div className="mb-6 text-center">
          <motion.div
            variants={containerVariants}
            className="auth-icon mb-4"
          >
            <UserPlus className="h-7 w-7" />
          </motion.div>
          <motion.h1 variants={containerVariants} className="text-3xl font-bold text-black">
            Create Account
          </motion.h1>
          <motion.p variants={containerVariants} className="mt-2 text-base text-black/62">
            Join us in a few quick steps
          </motion.p>
        </div>

            {/* Error Alert */}
            {(registerMutation.error || passwordError) && (
              <motion.div
                variants={containerVariants}
                role="alert"
                aria-live="polite"
                aria-atomic="true"
                className="mb-5 rounded-2xl border border-red-500/20 bg-red-50/80 px-4 py-3 text-sm font-medium text-red-700"
              >
                {passwordError || errorMessage}
              </motion.div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4" aria-label="Create account form">
              {/* Username Field */}
              <motion.div variants={containerVariants}>
                <label htmlFor="username" className="mb-2 block text-sm font-semibold text-black/82">
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4 text-blue-600" aria-hidden="true" />
                    Username
                  </div>
                </label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Choose a username"
                  required
                  className="auth-field"
                />
              </motion.div>

              {/* Email Field */}
              <motion.div variants={containerVariants}>
                <label htmlFor="email" className="mb-2 block text-sm font-semibold text-black/82">
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4 text-blue-600" aria-hidden="true" />
                    Email Address
                  </div>
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
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
                  placeholder="Create a strong password"
                  required
                  className="auth-field"
                />
                {password && (
                  <div className="mt-2 text-xs flex items-center gap-2" role="status" aria-live="polite">
                    {passwordStrengthOk ? (
                      <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" aria-hidden="true" />
                    ) : (
                      <div className="w-4 h-4 rounded-full bg-slate-300 flex-shrink-0" aria-hidden="true" />
                    )}
                    <span className={passwordStrengthOk ? 'text-green-700' : 'text-black/56'}>
                      At least 8 characters
                    </span>
                  </div>
                )}
              </motion.div>

              {/* Confirm Password Field */}
              <motion.div variants={containerVariants}>
                <label htmlFor="confirm-password" className="mb-2 block text-sm font-semibold text-black/82">
                  <div className="flex items-center gap-2">
                    <Lock className="h-4 w-4 text-blue-600" aria-hidden="true" />
                    Confirm Password
                  </div>
                </label>
                <input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    if (e.target.value && e.target.value !== password) {
                      setPasswordError('Passwords do not match');
                    } else {
                      setPasswordError('');
                    }
                  }}
                  placeholder="Confirm your password"
                  required
                  aria-describedby={passwordError ? 'password-error' : undefined}
                  className="auth-field"
                />
                {confirmPassword && (
                  <div id="password-status" className="mt-2 text-xs flex items-center gap-2" role="status" aria-live="polite">
                    {passwordsMatch ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" aria-hidden="true" />
                        <span className="text-green-700">Passwords match</span>
                      </>
                    ) : (
                      <>
                        <div className="w-4 h-4 rounded-full bg-red-500 flex-shrink-0" aria-hidden="true" />
                        <span className="text-red-700" id="password-error">Passwords do not match</span>
                      </>
                    )}
                  </div>
                )}
              </motion.div>

              {/* Terms Checkbox */}
              <motion.div
                variants={containerVariants}
                className="flex items-start gap-2 text-xs text-black/62"
              >
                <input
                  id="terms"
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  className="mt-0.5 h-4 w-4 cursor-pointer rounded border border-black/20 bg-white/70 accent-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  required
                  aria-label="I agree to the Terms of Service and Privacy Policy"
                />
                <label htmlFor="terms" className="cursor-pointer">
                  I agree to the{' '}
                  <Link href="/terms" className="rounded px-1 font-medium text-blue-700 transition hover:text-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-400">
                    Terms of Service
                  </Link>
                  {' '}and{' '}
                  <Link href="/privacy" className="rounded px-1 font-medium text-blue-700 transition hover:text-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-400">
                    Privacy Policy
                  </Link>
                </label>
              </motion.div>

              {/* Create Account Button */}
              <motion.div variants={containerVariants}>
                <button
                  type="submit"
                  disabled={registerMutation.isPending || !passwordsMatch || !termsAccepted || !passwordStrengthOk}
                  className="btn-liquid primary flex w-full items-center justify-center gap-2"
                >
                  {registerMutation.isPending ? (
                    <>
                      <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" role="status" aria-label="Creating account" />
                      Creating account...
                    </>
                  ) : (
                    <>
                      Create Account
                      <ChevronRight className="w-4 h-4" aria-hidden="true" />
                    </>
                  )}
                </button>
              </motion.div>
            </form>

            {/* Sign In Link */}
            <motion.div variants={containerVariants} className="auth-divider mt-6 border-t pt-6">
              <p className="text-center text-sm text-black/62">
                Already have an account?{' '}
                <Link
                  href="/login"
                  className="font-semibold text-blue-700 transition hover:text-blue-900"
                >
                  Sign in
                </Link>
              </p>
            </motion.div>
      </motion.div>
    </motion.div>
  );
}
