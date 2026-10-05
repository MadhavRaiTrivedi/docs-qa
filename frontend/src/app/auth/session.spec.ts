import { TestBed } from '@angular/core/testing';
import { Role } from './role';
import { Session } from './session';

describe('Session', () => {
  beforeEach(() => sessionStorage.clear());

  it('restores the signed-in user after a reload', () => {
    TestBed.inject(Session).signIn({ apiKey: 'key', role: Role.Editor });

    TestBed.resetTestingModule();
    const restored = TestBed.inject(Session);

    expect(restored.current()?.apiKey).toBe('key');
    expect(restored.isEditor()).toBe(true);
  });

  it('forgets the user on sign out', () => {
    const session = TestBed.inject(Session);
    session.signIn({ apiKey: 'key', role: Role.Reader });

    session.signOut();

    expect(session.isSignedIn()).toBe(false);
    expect(sessionStorage.length).toBe(0);
  });
});
