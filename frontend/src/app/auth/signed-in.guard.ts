import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Session } from './session';

export const signedInGuard: CanActivateFn = () =>
  inject(Session).isSignedIn() || inject(Router).createUrlTree(['/sign-in']);
