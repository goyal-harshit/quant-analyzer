'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { toast } from 'react-hot-toast'
import { Sparkles, Mail, Lock, ArrowRight, Eye } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { login } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password.trim()) {
      toast.error('Please enter email and password')
      return
    }

    setSubmitting(true)
    try {
      await login(email, password)
      toast.success('Logged in successfully!')
    } catch (err: any) {
      if (!err.response) {
        toast.error('Backend not reachable. Use "Explore as Guest" to browse without an account.')
      } else if (err.response?.status === 401) {
        toast.error('Incorrect email or password')
      } else {
        toast.error(err.response?.data?.detail || 'Login failed')
      }
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
            <Sparkles className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold text-textPrimary tracking-tight">Welcome back to QuantAI</h1>
          <p className="text-sm text-textSub">Enter your credentials to access your terminal</p>
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

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 py-3 bg-brand hover:bg-brand/90 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-brand/20 cursor-pointer"
          >
            {submitting ? 'Connecting...' : 'Access Terminal'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-border/50" />
          <span className="text-[10px] text-textMuted uppercase tracking-widest">or</span>
          <div className="flex-1 h-px bg-border/50" />
        </div>

        {/* Guest access */}
        <button
          onClick={() => router.push('/dashboard')}
          className="w-full flex items-center justify-center gap-2 py-2.5 bg-elevated hover:bg-border/40 border border-border/60 hover:border-brand/30 text-textSub hover:text-textPrimary rounded-lg text-sm font-medium transition-all"
        >
          <Eye className="w-4 h-4" />
          Explore as Guest
          <span className="text-[10px] text-textMuted">(no account needed)</span>
        </button>

        {/* Footer */}
        <div className="text-center text-xs text-textMuted">
          <span>Don't have an account? </span>
          <Link href="/register" className="text-brand hover:underline font-medium">
            Create an account
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
