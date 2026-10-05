import { DatePipe } from '@angular/common';
import { Component, inject, input, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { describeApiError, isServiceUnavailable } from '../shared/api-error';
import { AnswerView } from './answer-view';
import {
  AnswerEvent,
  AnswerOutcome,
  describeLocation,
  Question,
  Rating,
  SearchHit,
  Source,
} from './question.model';
import { QuestionsApi } from './questions.api';

const MIN_QUESTION_LENGTH = 3;
const MAX_QUESTION_LENGTH = 1000;

@Component({
  selector: 'app-ask-panel',
  imports: [ReactiveFormsModule, DatePipe, AnswerView],
  templateUrl: './ask-panel.html',
})
export class AskPanel implements OnInit {
  private readonly questionsApi = inject(QuestionsApi);

  readonly collectionId = input.required<string>();

  protected readonly describeLocation = describeLocation;
  protected readonly form = inject(FormBuilder).nonNullable.group({
    question: [
      '',
      [
        Validators.required,
        Validators.minLength(MIN_QUESTION_LENGTH),
        Validators.maxLength(MAX_QUESTION_LENGTH),
      ],
    ],
  });

  protected readonly isAsking = signal(false);
  protected readonly answer = signal('');
  protected readonly sources = signal<Source[]>([]);
  protected readonly outcome = signal<AnswerOutcome | null>(null);
  protected readonly questionId = signal<string | null>(null);
  protected readonly rating = signal<Rating | null>(null);
  protected readonly searchHits = signal<SearchHit[] | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly recent = signal<Question[]>([]);

  async ngOnInit(): Promise<void> {
    await this.loadRecent();
  }

  protected async ask(): Promise<void> {
    const question = this.form.getRawValue().question.trim();
    this.reset();
    this.isAsking.set(true);
    try {
      await this.questionsApi.ask(this.collectionId(), question, (event) => this.apply(event));
      await this.loadRecent();
    } catch (error) {
      if (isServiceUnavailable(error)) {
        await this.searchInstead(question);
      } else {
        this.error.set(describeApiError(error));
      }
    } finally {
      this.isAsking.set(false);
    }
  }

  protected show(question: Question): void {
    this.reset();
    this.form.setValue({ question: question.question });
    this.showSaved(question);
  }

  private apply(event: AnswerEvent): void {
    switch (event.type) {
      case 'sources':
        this.sources.set(event.sources);
        break;
      case 'delta':
        this.answer.update((answer) => answer + event.text);
        break;
      case 'done':
        this.showSaved(event.question);
        break;
      case 'error':
        this.error.set(event.detail);
        break;
    }
  }

  private showSaved(question: Question): void {
    this.answer.set(question.answer);
    this.sources.set(question.sources);
    this.outcome.set(question.outcome);
    this.questionId.set(question.id);
    this.rating.set(question.feedback?.rating ?? null);
  }

  // Without an OpenAI key the API cannot answer, but it can still show the matching passages.
  private async searchInstead(question: string): Promise<void> {
    try {
      this.searchHits.set(await this.questionsApi.search(this.collectionId(), question));
    } catch (error) {
      this.error.set(describeApiError(error));
    }
  }

  private reset(): void {
    this.answer.set('');
    this.sources.set([]);
    this.outcome.set(null);
    this.questionId.set(null);
    this.rating.set(null);
    this.searchHits.set(null);
    this.error.set(null);
  }

  private async loadRecent(): Promise<void> {
    try {
      this.recent.set(await this.questionsApi.recent(this.collectionId()));
    } catch (error) {
      this.error.set(describeApiError(error));
    }
  }
}
