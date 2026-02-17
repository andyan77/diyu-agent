"use client";

/**
 * Error boundary component for React error recovery.
 *
 * Task card: OS2-5
 * - Catches component crashes via React error boundary
 * - Reports errors to error-reporting service
 * - Renders fallback UI instead of white screen
 *
 * Architecture: 07-Deployment-Security Section 2
 */

import { Component, type ErrorInfo, type ReactNode } from "react";
import { reportError } from "../lib/error-reporting";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    reportError(error, {
      componentStack: errorInfo.componentStack ?? "",
      source: "ErrorBoundary",
    });
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div role="alert" data-testid="error-boundary-fallback">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message ?? "An unexpected error occurred."}</p>
          <button type="button" onClick={this.handleReset}>
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
