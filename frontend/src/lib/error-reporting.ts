/**
 * Whitfield Fulfillment Operations Platform - Frontend Error Reporting Helper
 * Captures application runtime exceptions for audit logging and developer diagnostics.
 */

export interface ErrorContext {
  boundary?: string;
  componentStack?: string | null;
  metadata?: Record<string, unknown>;
}

export function reportError(error: Error | unknown, context?: ErrorContext): void {
  const errorMessage = error instanceof Error ? error.message : String(error);
  const errorStack = error instanceof Error ? error.stack : undefined;

  console.error("[Whitfield Ops Error]", {
    message: errorMessage,
    stack: errorStack,
    boundary: context?.boundary ?? "unknown",
    metadata: context?.metadata ?? {},
    timestamp: new Date().toISOString(),
  });
}
