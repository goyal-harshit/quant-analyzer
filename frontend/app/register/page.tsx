'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/components/auth/AuthProvider'
import { toast } from 'react-hot-toast'
import { Sparkles, Mail, Lock, ArrowRight, UserPlus } from 'lucide-react'

export default function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { register } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password.trim()) {
      toast.error('Please enter email and password')
      return
    }

    if (password !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }

    setSubmitting(true)
    try {
      await register(email, password)
      toast.success('Account created successfully!')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md glass p-8 rounded-xl shadow-xl space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-brand/10 border border-brand/30 rounded-xl text-brand mb-2">
            <UserPlus className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold text-textPrimary tracking-tight">Create QuantAI Account</h1>
          <p className="text-sm text-textSub">Register your terminal to begin quant modeling</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-textSub uppercase tracking-wider">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-textMuted" />
              <input
                type="email"
                required
                className="w-full pl-10 pr-4 py-2.5 bg-elevated border border-border focus:border-brand hover:border-borderHi rounded-lg text-sm text-textPrimary placeholder-textMuted outline-none transition-all"
                placeholder="you@domain.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-textSub uppercase tracking-wider">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-textMuted" />
              <input
                type="password"
                required
                className="w-full pl-10 pr-4 py-2.5 bg-elevated border border-border focus:border-brand hover:border-borderHi rounded-lg text-sm text-textPrimary placeholder-textMuted outline-none transition-all"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-textSub uppercase tracking-wider">Confirm Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-textMuted" />
              <input
                type="password"
                required
                className="w-full pl-10 pr-4 py-2.5 bg-elevated border border-border focus:border-brand hover:border-borderHi rounded-lg text-sm text-textPrimary placeholder-textMuted outline-none transition-all"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 py-3 bg-brand hover:bg-brand/90 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-brand/20 cursor-pointer"
          >
            {submitting ? 'Creating Account...' : 'Register and Access'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {/* Footer */}
        <div className="text-center text-xs text-textMuted pt-2">
          <span>Already have an account? </span>
          <Link href="/login" className="text-brand hover:underline font-medium">
            Sign In
          </Link>
        </div>

        {/* Disclaimer */}
        <div className="text-center text-[10px] text-textMuted border-t border-border/50 pt-4">
          For educational purposes only. Not investment advice.
        </div>
      </div>
    </div>
  )
}
