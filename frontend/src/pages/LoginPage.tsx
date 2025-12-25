import { AuthForm } from '@/components/AuthForm'

export function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <AuthForm mode="login" />
    </div>
  )
}
