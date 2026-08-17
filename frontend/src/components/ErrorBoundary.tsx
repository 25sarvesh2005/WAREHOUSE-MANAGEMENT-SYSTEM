import React, { Component, type ErrorInfo, type ReactNode } from "react";
import { reportError } from "../lib/error-reporting";

export interface ErrorBoundaryProps {
  /** Component children to wrap with safety boundary. */
  children: ReactNode;
  /** Optional custom fallback component or render function. */
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  /** Identifier for audit logging and metrics. */
  name?: string;
  /** Optional callback fired when an error is caught. */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Optional callback fired when the boundary is reset. */
  onReset?: () => void;
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Standard React Error Boundary for the Whitfield Operations platform.
 * Catches JavaScript errors anywhere in their child component tree, logs them
 * to the error-reporting service, and displays a fallback UI instead of crashing
 * the whole application.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public override state: ErrorBoundaryState = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    reportError(error, {
      boundary: this.props.name ?? "ReactErrorBoundary",
      componentStack: errorInfo.componentStack ?? null,
    });

    this.props.onError?.(error, errorInfo);
  }

  public resetErrorBoundary = (): void => {
    this.props.onReset?.();
    this.setState({ hasError: false, error: null });
  };

  public override render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      if (typeof this.props.fallback === "function") {
        return this.props.fallback(this.state.error, this.resetErrorBoundary);
      }

      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[300px] w-full items-center justify-center rounded-lg border border-destructive/20 bg-destructive/5 p-6 text-center">
          <div className="max-w-md space-y-4">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-semibold text-foreground">
                Something went wrong in this section
              </h3>
              <p className="text-sm text-muted-foreground">
                An unexpected component error occurred. Other operations remain active.
              </p>
            </div>
            {this.state.error.message && (
              <p className="rounded bg-muted/60 px-3 py-1.5 text-xs font-mono text-muted-foreground break-words">
                {this.state.error.message}
              </p>
            )}
            <div className="flex justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={this.resetErrorBoundary}
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                Try again
              </button>
              <a
                href="/"
                className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                Dashboard
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
