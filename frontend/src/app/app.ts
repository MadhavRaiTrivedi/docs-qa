import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterOutlet } from '@angular/router';
import { Session } from './auth/session';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink],
  templateUrl: './app.html',
})
export class App {
  private readonly router = inject(Router);
  protected readonly session = inject(Session);

  protected async signOut(): Promise<void> {
    this.session.signOut();
    await this.router.navigate(['/sign-in']);
  }
}
