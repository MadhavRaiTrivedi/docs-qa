export enum AnswerOutcome {
  Answered = 'ANSWERED',
  NotInDocuments = 'NOT_IN_DOCUMENTS',
  Unsupported = 'UNSUPPORTED',
}

export enum Rating {
  Helpful = 'HELPFUL',
  NotHelpful = 'NOT_HELPFUL',
}

export interface Source {
  number: number;
  chunkId: string;
  documentId: string;
  fileName: string;
  pageNumber: number | null;
  headingPath: string[];
  text: string;
  score: number;
  similarity: number | null;
  isCited: boolean;
}

export interface Feedback {
  rating: Rating;
  comment: string | null;
  updatedAt: string;
}

export interface Question {
  id: string;
  collectionId: string;
  question: string;
  answer: string;
  outcome: AnswerOutcome;
  model: string | null;
  sources: Source[];
  inputTokens: number | null;
  outputTokens: number | null;
  cachedInputTokens: number | null;
  latencyMs: number;
  createdAt: string;
  feedback: Feedback | null;
}

export type AnswerEvent =
  | { type: 'sources'; sources: Source[] }
  | { type: 'delta'; text: string }
  | { type: 'done'; question: Question }
  | { type: 'error'; detail: string };

export function describeLocation(source: Pick<Source, 'pageNumber' | 'headingPath'>): string {
  const parts = source.pageNumber === null ? [] : [`page ${source.pageNumber}`];
  if (source.headingPath.length > 0) {
    parts.push(source.headingPath.join(' › '));
  }
  return parts.join(', ');
}
