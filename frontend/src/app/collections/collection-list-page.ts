import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Session } from '../auth/session';
import { describeApiError } from '../shared/api-error';
import { Collection } from './collection.model';
import { CollectionsApi } from './collections.api';

@Component({
  selector: 'app-collection-list-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './collection-list-page.html',
})
export class CollectionListPage implements OnInit {
  private readonly collectionsApi = inject(CollectionsApi);
  protected readonly session = inject(Session);

  protected readonly collections = signal<Collection[]>([]);
  protected readonly isLoading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly createForm = inject(FormBuilder).nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(100)]],
  });

  async ngOnInit(): Promise<void> {
    await this.load();
  }

  protected async create(): Promise<void> {
    this.error.set(null);
    try {
      await this.collectionsApi.create(this.createForm.getRawValue().name.trim());
      this.createForm.reset();
      await this.load();
    } catch (error) {
      this.error.set(describeApiError(error));
    }
  }

  private async load(): Promise<void> {
    this.isLoading.set(true);
    try {
      this.collections.set(await this.collectionsApi.list());
    } catch (error) {
      this.error.set(describeApiError(error));
    } finally {
      this.isLoading.set(false);
    }
  }
}
