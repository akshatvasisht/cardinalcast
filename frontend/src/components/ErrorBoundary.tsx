import { Component, type ReactNode } from 'react'

interface Props {
    children: ReactNode
    fallback?: ReactNode
}

interface State {
    hasError: boolean
}

export class ErrorBoundary extends Component<Props, State> {
    state: State = { hasError: false }

    static getDerivedStateFromError(_error: Error) {
        return { hasError: true }
    }

    componentDidCatch(error: Error, info: { componentStack: string }) {
        // Log the error for local debugging
        console.error('ErrorBoundary caught an error:', error, info)
    }

    render() {
        if (this.state.hasError) {
            return (
                this.props.fallback ?? (
                    <div className="flex min-h-[200px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-destructive/50 bg-destructive/5 p-8 text-center">
                        <h3 className="text-lg font-semibold text-destructive">Something went wrong</h3>
                        <p className="mt-2 text-sm text-muted-foreground">
                            An unexpected error occurred while rendering this component.
                        </p>
                        <button
                            onClick={() => this.setState({ hasError: false })}
                            className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                        >
                            Try again
                        </button>
                    </div>
                )
            )
        }

        return this.props.children
    }
}
