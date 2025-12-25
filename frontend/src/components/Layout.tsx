import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/Button'
import { Logo } from '@/components/ui/Logo'
import { BalatroBackground } from '@/components/BalatroBackground'
import { cn } from '@/lib/utils'

export function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <div className="relative min-h-screen font-['Outfit'] antialiased text-foreground selection:bg-primary/20">
      {/* Background Layer */}
      <div className="fixed inset-0 z-0 pointer-events-none opacity-50">
        <BalatroBackground
          isRotate={false}
          mouseInteraction={false}
          pixelFilter={745}
          color1="#C5050C"
          color2="#FFFFFF"
          color3="#1a1a1a"
        />
      </div>

      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-black/60 backdrop-blur-2xl">
        <div className="container mx-auto max-w-[1400px] flex h-16 items-center justify-between px-6">
          <div className="flex items-center gap-8">
            <Link to="/" className="font-bold flex items-center gap-3 text-2xl tracking-tight hover:opacity-90 transition-opacity">
              <div className="drop-shadow-[0_0_15px_rgba(197,5,12,0.4)]">
                <Logo className="h-10 w-10" />
              </div>
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-white/80">
                CardinalCast
              </span>
            </Link>
            <nav className="flex gap-2">
              <Button
                variant={location.pathname === '/' ? 'secondary' : 'ghost'}
                size="sm"
                asChild
                className={cn(
                  "rounded-full px-5 h-9 transition-all",
                  location.pathname === '/' ? "text-black font-bold" : "text-white/70 hover:text-white hover:bg-white/10"
                )}
              >
                <Link to="/">Dashboard</Link>
              </Button>

              <Button
                variant={location.pathname === '/wagers' && !location.pathname.startsWith('/wagers/new') ? 'secondary' : 'ghost'}
                size="sm"
                asChild
                className={cn(
                  "rounded-full px-5 h-9 transition-all",
                  location.pathname === '/wagers' && !location.pathname.startsWith('/wagers/new') ? "text-black font-bold" : "text-white/70 hover:text-white hover:bg-white/10"
                )}
              >
                <Link to="/wagers">History</Link>
              </Button>
              <Button
                variant={location.pathname === '/leaderboard' ? 'secondary' : 'ghost'}
                size="sm"
                asChild
                className={cn(
                  "rounded-full px-5 h-9 transition-all",
                  location.pathname === '/leaderboard' ? "text-black font-bold" : "text-white/70 hover:text-white hover:bg-white/10"
                )}
              >
                <Link to="/leaderboard">Leaderboard</Link>
              </Button>
            </nav>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex flex-col items-end gap-0.5">
              <span className="text-[10px] uppercase font-bold tracking-[0.2em] text-white/50">{user?.username ?? '—'}</span>
              <span className="text-sm font-bold text-white">Credits: {user?.credits_balance ?? 0}</span>
            </div>
            <Button variant="outline" size="sm" onClick={logout} className="rounded-full border-white/20 bg-white/5 hover:bg-white text-white hover:text-black transition-all h-9 px-5">
              Logout
            </Button>
          </div>
        </div>
      </header>
      <main className="container relative z-10 mx-auto max-w-[1400px] px-6 py-8 mt-16">
        <Outlet />
      </main>
    </div>
  )
}
