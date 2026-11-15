import { Component, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  title: string
  children: ReactNode
}

interface ErrorBoundaryState {
  message: string | null
}

export class ScreenErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { message: null }

  static getDerivedStateFromError(error: unknown): ErrorBoundaryState {
    return {
      message: error instanceof Error ? error.message : 'This screen failed to load.',
    }
  }

  render() {
    if (this.state.message) {
      return (
        <div className="grid h-full place-items-center p-6">
          <div className="max-w-md rounded-lg border border-line bg-panel p-5">
            <p className="text-sm font-medium text-paper">{this.props.title}</p>
            <p className="mt-2 text-sm text-mist">{this.state.message}</p>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
