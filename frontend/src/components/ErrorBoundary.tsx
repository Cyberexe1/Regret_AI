import { Component, type ErrorInfo, type ReactNode } from 'react';
import { RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Changing this resets the boundary, e.g. on navigation. */
  resetKey?: string;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Catches render failures so one broken view cannot blank the whole app. The
 * shell stays mounted around it, which keeps navigation available.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  override componentDidUpdate(previous: ErrorBoundaryProps) {
    if (this.state.error && previous.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    // No telemetry sink yet; surfacing it in the console is the honest option.
    console.error('Render failed:', error, info.componentStack);
  }

  override render() {
    const { error } = this.state;

    if (!error) return this.props.children;

    return (
      <div className="px-[var(--page-gutter)] py-10">
        <ErrorState
          className="mx-auto max-w-lg"
          title="This view failed to load"
          description="Something went wrong rendering this page. Navigating elsewhere still works."
          detail={error.message}
          action={
            <Button
              variant="secondary"
              leftIcon={RotateCcw}
              onClick={() => this.setState({ error: null })}
            >
              Try again
            </Button>
          }
        />
      </div>
    );
  }
}
