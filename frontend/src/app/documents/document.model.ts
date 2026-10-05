export enum DocumentStatus {
  Uploaded = 'UPLOADED',
  Processing = 'PROCESSING',
  Ready = 'READY',
  Failed = 'FAILED',
}

export enum FileFormat {
  Pdf = 'PDF',
  Markdown = 'MARKDOWN',
  PlainText = 'PLAIN_TEXT',
}

export interface LibraryDocument {
  id: string;
  collectionId: string;
  fileName: string;
  format: FileFormat;
  sizeBytes: number;
  status: DocumentStatus;
  failureReason: string | null;
  attempts: number;
  pageCount: number | null;
  chunkCount: number;
  replacesDocumentId: string | null;
  createdAt: string;
  readyAt: string | null;
}

export const ACCEPTED_FILE_TYPES = '.pdf,.md,.markdown,.txt';

export function isInProgress(document: LibraryDocument): boolean {
  return (
    document.status === DocumentStatus.Uploaded || document.status === DocumentStatus.Processing
  );
}
