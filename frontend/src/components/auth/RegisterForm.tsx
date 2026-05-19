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
      className="min-h-screen flex items-center justify-center bg-white px-4 py-12"
    >
      <motion.div variants={containerVariants} className="relative w-full max-w-md">
        {/* Header Section */}
        <div className="mb-8 text-center">
          <motion.div
            variants={containerVariants}
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 mb-4"
          >
            <UserPlus className="w-8 h-8 text-white" />
          </motion.div>
          <motion.h1 variants={containerVariants} className="text-3xl font-bold text-slate-900">
            Create Account
          </motion.h1>
          <motion.p variants={containerVariants} className="mt-2 text-slate-600 text-base">
            Join us in a few quick steps
          </motion.p>
        </div>

        {/* Clean Card Container */}
        <motion.div variants={containerVariants}>
          <div className="rounded-2xl bg-white shadow-2xl border border-slate-100 p-8">
            {/* Error Alert */}
            {(registerMutation.error || passwordError) && (
              <motion.div
                variants={containerVariants}
                role="alert"
                aria-live="polite"
                aria-atomic="true"
                className="mb-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-red-700 text-sm"
              >
                {passwordError || errorMessage}
              </motion.div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4" aria-label="Create account form">
              {/* Username Field */}
              <motion.div variants={containerVariants}>
                <label htmlFor="username" className="block text-sm font-medium text-slate-900 mb-2">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-blue-600" aria-hidden="true" />
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
                  className="input-base"
                />
              </motion.div>

              {/* Email Field */}
              <motion.div variants={containerVariants}>
                <label htmlFor="email" className="block text-sm font-medium text-slate-900 mb-2">
                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-blue-600" aria-hidden="true" />
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
                  placeholder="Create a strong password"
                  required
                  className="input-base"
                />
                {password && (
                  <div className="mt-2 text-xs flex items-center gap-2" role="status" aria-live="polite">
                    {passwordStrengthOk ? (
                      <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" aria-hidden="true" />
                    ) : (
                      <div className="w-4 h-4 rounded-full bg-slate-300 flex-shrink-0" aria-hidden="true" />
                    )}
                    <span className={passwordStrengthOk ? 'text-green-700' : 'text-slate-600'}>
                      At least 8 characters
                    </span>
                  </div>
                )}
              </motion.div>

              {/* Confirm Password Field */}
              <motion.div variants={containerVariants}>
                <label htmlFor="confirm-password" className="block text-sm font-medium text-slate-900 mb-2">
                  <div className="flex items-center gap-2">
                    <Lock className="w-4 h-4 text-blue-600" aria-hidden="true" />
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
                  className="input-base"
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
                className="flex items-start gap-2 text-xs text-slate-700"
              >
                <input
                  id="terms"
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  className="rounded w-4 h-4 mt-0.5 border border-slate-300 bg-white checked:bg-blue-600 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-600 accent-blue-600"
                  required
                  aria-label="I agree to the Terms of Service and Privacy Policy"
                />
                <label htmlFor="terms" className="cursor-pointer">
                  I agree to the{' '}
                  <Link href="/terms" className="text-blue-600 hover:text-blue-700 transition focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 rounded px-1">
                    Terms of Service
                  </Link>
                  {' '}and{' '}
                  <Link href="/privacy" className="text-blue-600 hover:text-blue-700 transition focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 rounded px-1">
                    Privacy Policy
                  </Link>
                </label>
              </motion.div>

              {/* Create Account Button */}
              <motion.div variants={containerVariants}>
                <button
                  type="submit"
                  disabled={registerMutation.isPending || !passwordsMatch || !termsAccepted || !passwordStrengthOk}
                  className="btn-primary w-full justify-center gap-2"
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
            <motion.div variants={containerVariants} className="mt-6 pt-6 border-t border-slate-200">
              <p className="text-center text-sm text-slate-700">
                Already have an account?{' '}
                <Link
                  href="/login"
                  className="font-semibold text-blue-600 hover:text-blue-700 transition"
                >
                  Sign in
                </Link>
              </p>
            </motion.div>
          </div>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}
