import { computed, Injectable, signal } from '@angular/core';
import { Role } from './role';

export interface SignedInUser {
  apiKey: string;
  role: Role;
}

const STORAGE_KEY = 'docs-qa.session';

@Injectable({ providedIn: 'root' })
export class Session {
  private readonly user = signal<SignedInUser | null>(Session.restore());

  readonly current = this.user.asReadonly();
  readonly isSignedIn = computed(() => this.user() !== null);
  readonly isEditor = computed(() => this.user()?.role === Role.Editor);

  signIn(user: SignedInUser): void {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    this.user.set(user);
  }

  signOut(): void {
    sessionStorage.removeItem(STORAGE_KEY);
    this.user.set(null);
  }

  private static restore(): SignedInUser | null {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    return stored ? (JSON.parse(stored) as SignedInUser) : null;
  }
}
