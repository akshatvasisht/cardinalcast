
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/Card'
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/components/ui/Form'
import { Input } from '@/components/ui/Input'

const schema = z.object({
    username: z.string().min(1, 'Username required'),
    password: z.string().min(1, 'Password required'),
})
type FormValues = z.infer<typeof schema>

interface AuthFormProps {
    mode: 'login' | 'register'
}

export function AuthForm({ mode }: AuthFormProps) {
    const { login } = useAuth()
    const navigate = useNavigate()
    const location = useLocation()
    const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? '/'

    const form = useForm<FormValues>({
        resolver: zodResolver(schema),
        defaultValues: { username: '', password: '' },
    })

    async function onSubmit(values: FormValues) {
        try {
            let access_token: string
            if (mode === 'login') {
                const res = await api.login(values.username, values.password)
                access_token = res.access_token
            } else {
                const res = await api.register(values.username, values.password)
                access_token = res.access_token
            }

            login(access_token)
            navigate(mode === 'login' ? from : '/', { replace: true })
        } catch (e) {
            form.setError('root', { message: e instanceof Error ? e.message : 'Authentication failed' })
        }
    }

    const isLogin = mode === 'login'

    return (
        <Card className="w-full max-w-sm">
            <CardHeader>
                <CardTitle>{isLogin ? 'Log in' : 'Register'}</CardTitle>
                <CardDescription>
                    {isLogin ? 'Enter your CardinalCast credentials.' : 'Create a CardinalCast account.'}
                </CardDescription>
            </CardHeader>
            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)}>
                    <CardContent className="space-y-4">
                        {form.formState.errors.root && (
                            <p className="text-sm font-medium text-destructive" role="alert" aria-live="polite">{form.formState.errors.root.message}</p>
                        )}
                        <FormField
                            control={form.control}
                            name="username"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Username</FormLabel>
                                    <FormControl>
                                        <Input placeholder="alice" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="password"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Password</FormLabel>
                                    <FormControl>
                                        <Input type="password" placeholder="••••••••" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </CardContent>
                    <CardFooter className="flex flex-col gap-2">
                        <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
                            {form.formState.isSubmitting ? (isLogin ? 'Signing in…' : 'Registering…') : (isLogin ? 'Log in' : 'Register')}
                        </Button>
                        <p className="text-center text-sm text-muted-foreground">
                            {isLogin ? "No account? " : "Already have an account? "}
                            <Link to={isLogin ? "/register" : "/login"} className="text-primary underline">
                                {isLogin ? "Register" : "Log in"}
                            </Link>
                        </p>
                    </CardFooter>
                </form>
            </Form>
        </Card>
    )
}
