import { HttpErrorResponse, HttpInterceptorFn, HttpStatusCode } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { API_KEY_HEADER } from '../shared/http-headers';
import { Session } from './session';

export const apiKeyInterceptor: HttpInterceptorFn = (request, next) => {
  const session = inject(Session);
  const router = inject(Router);
  const apiKey = session.current()?.apiKey;

  const authorized =
    apiKey && !request.headers.has(API_KEY_HEADER)
      ? request.clone({ setHeaders: { [API_KEY_HEADER]: apiKey } })
      : request;

  return next(authorized).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === HttpStatusCode.Unauthorized) {
        session.signOut();
        void router.navigate(['/sign-in']);
      }
      return throwError(() => error);
    }),
  );
};
