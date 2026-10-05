import { Routes } from '@angular/router';
import { signedInGuard } from './auth/signed-in.guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'collections' },
  {
    path: 'sign-in',
    title: 'Sign in',
    loadComponent: () => import('./auth/sign-in-page').then((m) => m.SignInPage),
  },
  {
    path: 'collections',
    title: 'Collections',
    canActivate: [signedInGuard],
    loadComponent: () =>
      import('./collections/collection-list-page').then((m) => m.CollectionListPage),
  },
  {
    path: 'collections/:id',
    title: 'Collection',
    canActivate: [signedInGuard],
    loadComponent: () => import('./collections/collection-page').then((m) => m.CollectionPage),
  },
  { path: '**', redirectTo: 'collections' },
];
