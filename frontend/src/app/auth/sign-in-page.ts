import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { describeApiError } from '../shared/api-error';
import { AuthApi } from './auth.api';
import { Session } from './session';

@Component({
  selector: 'app-sign-in-page',
  imports: [ReactiveFormsModule],
  templateUrl: './sign-in-page.html',
})
export class SignInPage {
  private readonly authApi = inject(AuthApi);
  private readonly session = inject(Session);
  private readonly router = inject(Router);

  protected readonly error = signal<string | null>(null);
  protected readonly isSubmitting = signal(false);
  protected readonly form = inject(FormBuilder).nonNullable.group({
    apiKey: ['', Validators.required],
  });

  protected async signIn(): Promise<void> {
    const apiKey = this.form.getRawValue().apiKey.trim();
    this.isSubmitting.set(true);
    this.error.set(null);
    try {
      this.session.signIn({ apiKey, role: await this.authApi.roleFor(apiKey) });
      await this.router.navigate(['/collections']);
    } catch (error) {
      this.error.set(describeApiError(error));
    } finally {
      this.isSubmitting.set(false);
    }
  }
}
