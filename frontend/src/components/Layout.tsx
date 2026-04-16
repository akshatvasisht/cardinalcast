import { Suspense, useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Logo } from '@/components/ui/Logo'
import { BalatroBackground } from '@/components/BalatroBackground'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/Dialog'
import { Gift, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { BALATRO_COLORS } from '@/lib/constants'

export function Layout() {
  const { user, logout, token, setUser } = useAuth()
  const location = useLocation()

  const navItems = [
    { to: '/', label: 'Dashboard', active: location.pathname === '/' },
    { to: '/wagers', label: 'History', active: location.pathname === '/wagers' },
    { to: '/leaderboard', label: 'Leaderboard', active: location.pathname === '/leaderboard' },
  ]

  // ── Daily claim (runs once on mount, never re-triggers on navigation) ──────
  const [claimOpen, setClaimOpen] = useState(false)
  const [claiming, setClaiming] = useState(false)
  const [claimed, setClaimed] = useState(false)

  useEffect(() => {
    if (!token) return
    api.dailyStatus(token)
      .then((r) => { if (r.status === 'AVAILABLE') setClaimOpen(true) })
      .catch(() => { })
  }, [token])

  async function handleClaim() {
    if (!token) return
    setClaiming(true)
    try {
      await api.dailyClaim(token)
      setClaimed(true)
      const updated = await api.me(token)
      setUser(updated)
      setTimeout(() => {
        setClaimOpen(false)
        setClaimed(false)
      }, 1800)
    } catch {
      setClaimOpen(false)
    } finally {
      setClaiming(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden font-['Outfit'] antialiased text-foreground selection:bg-primary/20">
      {/* Skip to main content — screen readers and keyboard users */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground focus:shadow-lg"
      >
        Skip to content
      </a>

      <div className="fixed inset-0 z-0 pointer-events-none opacity-50">
        <BalatroBackground
          isRotate={false}
          mouseInteraction={false}
          pixelFilter={745}
          {...BALATRO_COLORS}
        />
      </div>

      {/* Daily Claim Dialog */}
      <Dialog open={claimOpen} onOpenChange={(o) => { if (!claiming) setClaimOpen(o) }}>
        <DialogContent className="max-w-sm p-0 overflow-hidden">
          <DialogTitle className="sr-only">Daily Credits</DialogTitle>
          <div className="relative flex flex-col items-center gap-3 px-6 pt-8 pb-6 text-center">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/20 via-transparent to-transparent" />
            {claimed ? (
              <>
                <div className="relative z-10 flex h-14 w-14 items-center justify-center rounded-full bg-success/15 ring-2 ring-success/30">
                  <CheckCircle2 className="h-7 w-7 text-success" />
                </div>
                <div className="relative z-10 space-y-1">
                  <p className="text-xl font-bold text-success">+100 credits</p>
                  <p className="text-sm text-muted-foreground">Added to your balance</p>
                </div>
              </>
            ) : (
              <>
                <div className="relative z-10 flex h-14 w-14 items-center justify-center rounded-full bg-primary/15 ring-2 ring-primary/30">
                  <Gift className="h-7 w-7 text-primary" />
                </div>
                <div className="relative z-10 space-y-1">
                  <p className="text-xl font-bold">Daily Credits</p>
                  <p className="text-sm text-muted-foreground">Your 100 credits are ready to claim</p>
                </div>
                <p className="relative z-10 text-4xl font-bold tabular-nums text-primary">100</p>
              </>
            )}
          </div>
          {!claimed && (
            <div className="flex gap-2 border-t px-6 py-4">
              <Button variant="ghost" className="flex-1" onClick={() => setClaimOpen(false)}>
                Later
              </Button>
              <Button className="flex-1" onClick={handleClaim} disabled={claiming}>
                {claiming ? 'Claiming…' : 'Claim Now'}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-black/60 backdrop-blur-2xl">
        <div className="container mx-auto max-w-[1400px] flex h-16 items-center justify-between px-6">
          {/* Logo + Nav */}
          <div className="flex items-center gap-8 min-w-0">
            <Link
              to="/"
              className="font-bold flex items-center gap-3 text-2xl tracking-tight hover:opacity-90 transition-opacity flex-shrink-0"
            >
              <div className="drop-shadow-[0_0_15px_rgba(197,5,12,0.4)]">
                <Logo className="h-10 w-10" />
              </div>
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-white/80">
                CardinalCast
              </span>
            </Link>

            <nav className="flex gap-1" aria-label="Main navigation">
              {navItems.map(({ to, label, active }) => (
                <Button
                  key={to}
                  variant={active ? 'secondary' : 'ghost'}
                  size="sm"
                  asChild
                  className={cn(
                    'rounded-full px-5 h-9 text-sm transition-all',
                    active
                      ? 'text-black font-bold'
                      : 'text-white/70 hover:text-white hover:bg-white/10'
                  )}
                >
                  <Link to={to} aria-current={active ? 'page' : undefined}>
                    {label}
                  </Link>
                </Button>
              ))}
            </nav>
          </div>

          {/* User area */}
          <div className="flex items-center gap-6 flex-shrink-0">
            <div className="flex flex-col items-end gap-0.5">
              <span className="text-[10px] uppercase font-bold tracking-[0.2em] text-white/50">
                {user?.username ?? '—'}
              </span>
              <span className="text-sm font-bold text-white">
                Credits: {user?.credits_balance ?? 0}
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={logout}
              className="rounded-full border-white/20 bg-white/5 hover:bg-white text-white hover:text-black transition-all h-9 px-5 text-sm"
            >
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main id="main-content" className="container relative z-10 mx-auto max-w-[1400px] px-6 py-8 mt-16">
        <Suspense fallback={<div className="page-transition-fallback" />}>
          <div key={location.pathname} className="page-transition">
            <Outlet />
          </div>
        </Suspense>
      </main>
    </div>
  )
}
