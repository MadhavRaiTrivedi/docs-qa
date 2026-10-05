import { HttpErrorResponse, HttpStatusCode } from '@angular/common/http';

export interface ProblemDetails {
  title?: string;
  detail?: string;
  status?: number;
  errors?: Record<string, string[]>;
}

/** A ProblemDetails response read with fetch, which Angular's HttpClient does not see. */
export class ProblemError extends Error {
  constructor(
    readonly status: number,
    readonly problem: ProblemDetails,
  ) {
    super(problem.detail ?? problem.title ?? `Request failed with status ${status}.`);
  }
}

export function describeApiError(error: unknown): string {
  if (error instanceof ProblemError) {
    return describeProblem(error.problem, error.status);
  }

  if (!(error instanceof HttpErrorResponse)) {
    return 'Something went wrong. Please try again.';
  }

  if (error.status === 0) {
    return 'The API is unreachable. Check that the backend is running.';
  }

  return describeProblem(error.error as ProblemDetails | null, error.status);
}

export function isServiceUnavailable(error: unknown): boolean {
  const status =
    error instanceof ProblemError || error instanceof HttpErrorResponse ? error.status : null;
  return status === HttpStatusCode.ServiceUnavailable;
}

function describeProblem(problem: ProblemDetails | null, status: number): string {
  const validationMessages = Object.entries(problem?.errors ?? {}).flatMap(([field, messages]) =>
    messages.map((message) => (field ? `${field}: ${message}` : message)),
  );
  if (validationMessages.length > 0) {
    return validationMessages.join(' ');
  }

  return problem?.detail ?? problem?.title ?? `Request failed with status ${status}.`;
}
