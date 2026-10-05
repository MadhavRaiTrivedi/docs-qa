import { Component, inject, input, OnInit, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Session } from '../auth/session';
import { DocumentPanel } from '../documents/document-panel';
import { AskPanel } from '../questions/ask-panel';
import { describeApiError } from '../shared/api-error';
import { Collection } from './collection.model';
import { CollectionsApi } from './collections.api';

@Component({
  selector: 'app-collection-page',
  imports: [RouterLink, AskPanel, DocumentPanel],
  templateUrl: './collection-page.html',
})
export class CollectionPage implements OnInit {
  private readonly collectionsApi = inject(CollectionsApi);
  private readonly router = inject(Router);
  protected readonly session = inject(Session);

  readonly id = input.required<string>();

  protected readonly collection = signal<Collection | null>(null);
  protected readonly error = signal<string | null>(null);

  async ngOnInit(): Promise<void> {
    try {
      this.collection.set(await this.collectionsApi.get(this.id()));
    } catch (error) {
      this.error.set(describeApiError(error));
    }
  }

  protected async remove(collection: Collection): Promise<void> {
    if (!confirm(`Delete ${collection.name} and all its documents?`)) {
      return;
    }
    try {
      await this.collectionsApi.delete(collection.id);
      await this.router.navigate(['/collections']);
    } catch (error) {
      this.error.set(describeApiError(error));
    }
  }
}
