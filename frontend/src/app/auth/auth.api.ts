import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { API_KEY_HEADER } from '../shared/http-headers';
import { Role } from './role';

@Injectable({ providedIn: 'root' })
export class AuthApi {
  private readonly http = inject(HttpClient);

  async roleFor(apiKey: string): Promise<Role> {
    const me = await firstValueFrom(
      this.http.get<{ role: Role }>('/api/me', { headers: { [API_KEY_HEADER]: apiKey } }),
    );
    return me.role;
  }
}
