import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { LibraryDocument } from './document.model';

@Injectable({ providedIn: 'root' })
export class DocumentsApi {
  private readonly http = inject(HttpClient);

  list(collectionId: string): Promise<LibraryDocument[]> {
    return firstValueFrom(
      this.http.get<LibraryDocument[]>(`/api/collections/${collectionId}/documents`),
    );
  }

  upload(collectionId: string, file: File): Promise<LibraryDocument> {
    return firstValueFrom(
      this.http.post<LibraryDocument>(
        `/api/collections/${collectionId}/documents`,
        DocumentsApi.form(file),
      ),
    );
  }

  uploadVersion(documentId: string, file: File): Promise<LibraryDocument> {
    return firstValueFrom(
      this.http.post<LibraryDocument>(
        `/api/documents/${documentId}/versions`,
        DocumentsApi.form(file),
      ),
    );
  }

  retry(documentId: string): Promise<LibraryDocument> {
    return firstValueFrom(
      this.http.post<LibraryDocument>(`/api/documents/${documentId}/retry`, {}),
    );
  }

  delete(documentId: string): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/documents/${documentId}`));
  }

  private static form(file: File): FormData {
    const form = new FormData();
    form.append('file', file);
    return form;
  }
}
