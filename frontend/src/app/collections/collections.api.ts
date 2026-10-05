import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Collection } from './collection.model';

@Injectable({ providedIn: 'root' })
export class CollectionsApi {
  private readonly http = inject(HttpClient);

  list(): Promise<Collection[]> {
    return firstValueFrom(this.http.get<Collection[]>('/api/collections'));
  }

  get(collectionId: string): Promise<Collection> {
    return firstValueFrom(this.http.get<Collection>(`/api/collections/${collectionId}`));
  }

  create(name: string): Promise<Collection> {
    return firstValueFrom(this.http.post<Collection>('/api/collections', { name }));
  }

  delete(collectionId: string): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/collections/${collectionId}`));
  }
}
