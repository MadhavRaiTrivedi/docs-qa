import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Session } from '../auth/session';
import { ProblemDetails, ProblemError } from '../shared/api-error';
import { API_KEY_HEADER } from '../shared/http-headers';
import { AnswerEvent, Question, Rating, Source } from './question.model';
import { SseParser } from './sse-parser';

@Injectable({ providedIn: 'root' })
export class QuestionsApi {
  private readonly http = inject(HttpClient);
  private readonly session = inject(Session);

  /**
   * Streams an answer. HttpClient buffers the whole response before emitting, so this uses
   * fetch and reads the Server-Sent Events as they arrive.
   */
  async ask(
    collectionId: string,
    question: string,
    onEvent: (event: AnswerEvent) => void,
  ): Promise<void> {
    const response = await fetch(`/api/collections/${collectionId}/questions/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        [API_KEY_HEADER]: this.session.current()?.apiKey ?? '',
      },
      body: JSON.stringify({ question }),
    });
    if (!response.ok || !response.body) {
      throw new ProblemError(response.status, (await response.json()) as ProblemDetails);
    }

    const parser = new SseParser();
    const decoder = new TextDecoder();
    const reader = response.body.getReader();
    for (let chunk = await reader.read(); !chunk.done; chunk = await reader.read()) {
      for (const event of parser.push(decoder.decode(chunk.value, { stream: true }))) {
        onEvent(QuestionsApi.toAnswerEvent(event.name, JSON.parse(event.data)));
      }
    }
  }

  recent(collectionId: string): Promise<Question[]> {
    return firstValueFrom(this.http.get<Question[]>(`/api/collections/${collectionId}/questions`));
  }

  get(questionId: string): Promise<Question> {
    return firstValueFrom(this.http.get<Question>(`/api/questions/${questionId}`));
  }

  rate(questionId: string, rating: Rating): Promise<void> {
    return firstValueFrom(this.http.put<void>(`/api/questions/${questionId}/feedback`, { rating }));
  }

  private static toAnswerEvent(name: string, payload: unknown): AnswerEvent {
    switch (name) {
      case 'sources':
        return { type: 'sources', sources: payload as Source[] };
      case 'delta':
        return { type: 'delta', text: (payload as { text: string }).text };
      case 'done':
        return { type: 'done', question: payload as Question };
      default:
        return { type: 'error', detail: (payload as ProblemDetails).detail ?? 'Unknown error.' };
    }
  }
}
