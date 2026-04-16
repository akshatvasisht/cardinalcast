import { AuthForm } from '@/components/AuthForm'
import { BalatroBackground } from '@/components/BalatroBackground'
import { Logo } from '@/components/ui/Logo'
import { BALATRO_COLORS } from '@/lib/constants'

export function LoginPage() {
  return (
    <div className="relative flex min-h-screen items-center justify-center p-4">
      <div className="fixed inset-0 z-0 pointer-events-none opacity-50">
        <BalatroBackground
          isRotate={false}
          mouseInteraction={false}
          pixelFilter={745}
          {...BALATRO_COLORS}
        />
      </div>
      <div className="relative z-10 w-full max-w-sm flex flex-col items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="drop-shadow-[0_0_15px_rgba(197,5,12,0.4)]">
            <Logo className="h-10 w-10" />
          </div>
          <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/80">
            CardinalCast
          </span>
        </div>
        <AuthForm mode="login" />
      </div>
    </div>
  )
}
