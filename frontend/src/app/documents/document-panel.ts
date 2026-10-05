import { DecimalPipe } from '@angular/common';
import { Component, DestroyRef, inject, input, OnInit, signal } from '@angular/core';
import { Session } from '../auth/session';
import { describeApiError } from '../shared/api-error';
import {
  ACCEPTED_FILE_TYPES,
  DocumentStatus,
  isInProgress,
  LibraryDocument,
} from './document.model';
import { DocumentsApi } from './documents.api';

const POLL_INTERVAL_MS = 2000;
const BYTES_PER_KILOBYTE = 1024;

@Component({
  selector: 'app-document-panel',
  imports: [DecimalPipe],
  templateUrl: './document-panel.html',
})
export class DocumentPanel implements OnInit {
  private readonly documentsApi = inject(DocumentsApi);
  protected readonly session = inject(Session);

  readonly collectionId = input.required<string>();

  protected readonly DocumentStatus = DocumentStatus;
  protected readonly acceptedFileTypes = ACCEPTED_FILE_TYPES;
  protected readonly bytesPerKilobyte = BYTES_PER_KILOBYTE;
  protected readonly documents = signal<LibraryDocument[]>([]);
  protected readonly isUploading = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() {
    // Ingestion runs in the background, so refresh while any document is still in progress.
    const timer = setInterval(() => {
      if (this.documents().some(isInProgress)) {
        void this.load();
      }
    }, POLL_INTERVAL_MS);
    inject(DestroyRef).onDestroy(() => clearInterval(timer));
  }

  async ngOnInit(): Promise<void> {
    await this.load();
  }

  protected async upload(event: Event): Promise<void> {
    const files = Array.from((event.target as HTMLInputElement).files ?? []);
    await this.run(() =>
      Promise.all(files.map((file) => this.documentsApi.upload(this.collectionId(), file))),
    );
    (event.target as HTMLInputElement).value = '';
  }

  protected async replace(document: LibraryDocument, event: Event): Promise<void> {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) {
      await this.run(() => this.documentsApi.uploadVersion(document.id, file));
    }
  }

  protected async retry(document: LibraryDocument): Promise<void> {
    await this.run(() => this.documentsApi.retry(document.id));
  }

  protected async remove(document: LibraryDocument): Promise<void> {
    if (confirm(`Delete ${document.fileName}? Its passages will no longer be searched.`)) {
      await this.run(() => this.documentsApi.delete(document.id));
    }
  }

  private async run(action: () => Promise<unknown>): Promise<void> {
    this.isUploading.set(true);
    this.error.set(null);
    try {
      await action();
      await this.load();
    } catch (error) {
      this.error.set(describeApiError(error));
    } finally {
      this.isUploading.set(false);
    }
  }

  private async load(): Promise<void> {
    try {
      this.documents.set(await this.documentsApi.list(this.collectionId()));
    } catch (error) {
      this.error.set(describeApiError(error));
    }
  }
}
