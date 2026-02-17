/**
 * Error reporting service for DIYU Agent frontend.
 *
 * Task card: OS2-5
 * - Reports errors to configured backend or Sentry-equivalent
 * - Redacts sensitive data before reporting
 * - Provides a pluggable interface for different reporting backends
 *
 * Architecture: 07-Deployment-Security Section 2
 */

export interface ErrorContext {
  componentStack?: string;
  source?: string;
  userId?: string;
  orgId?: string;
  url?: string;
  [key: string]: unknown;
}

interface ErrorReport {
  message: string;
  stack: string;
  context: ErrorContext;
  timestamp: string;
  userAgent: string;
}

const SENSITIVE_KEYS = new Set([
  "password",
  "token",
  "secret",
  "apiKey",
  "authorization",
  "cookie",
  "jwt",
  "credential",
]);

function redactSensitive(context: ErrorContext): ErrorContext {
  const result: ErrorContext = {};
  for (const [key, value] of Object.entries(context)) {
    if (SENSITIVE_KEYS.has(key.toLowerCase())) {
      result[key] = "[REDACTED]";
    } else {
      result[key] = value;
    }
  }
  return result;
}

function buildReport(error: Error, context: ErrorContext): ErrorReport {
  return {
    message: error.message,
    stack: error.stack ?? "",
    context: redactSensitive(context),
    timestamp: new Date().toISOString(),
    userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "ssr",
  };
}

/**
 * Report an error to the error tracking service.
 *
 * In production this sends to the configured backend endpoint.
 * In development/test it logs to console.
 */
export function reportError(error: Error, context: ErrorContext = {}): void {
  const report = buildReport(error, context);

  const endpoint = process.env.NEXT_PUBLIC_ERROR_REPORTING_URL;
  if (endpoint) {
    // Fire-and-forget POST to error reporting endpoint
    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report),
    }).catch(() => {
      // Silently ignore reporting failures to avoid cascading errors
    });
  }

  if (process.env.NODE_ENV !== "production") {
    // eslint-disable-next-line no-console
    console.error("[ErrorReporting]", report);
  }
}
