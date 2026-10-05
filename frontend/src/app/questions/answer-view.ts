import { Component, computed, inject, input, linkedSignal, signal } from '@angular/core';
import { describeApiError } from '../shared/api-error';
import { splitCitations } from './answer-segments';
import { AnswerOutcome, describeLocation, Rating, Source } from './question.model';
import { QuestionsApi } from './questions.api';

@Component({
  selector: 'app-answer-view',
  templateUrl: './answer-view.html',
})
export class AnswerView {
  private readonly questionsApi = inject(QuestionsApi);

  readonly answer = input.required<string>();
  readonly sources = input.required<Source[]>();
  readonly outcome = input<AnswerOutcome | null>(null);
  readonly questionId = input<string | null>(null);
  readonly rating = input<Rating | null>(null);

  protected readonly AnswerOutcome = AnswerOutcome;
  protected readonly Rating = Rating;
  protected readonly describeLocation = describeLocation;
  protected readonly segments = computed(() =>
    splitCitations(this.answer(), this.sources().length),
  );
  protected readonly highlighted = signal<number | null>(null);
  protected readonly currentRating = linkedSignal(() => this.rating());
  protected readonly feedbackError = signal<string | null>(null);

  protected showSource(number: number): void {
    this.highlighted.set(number);
    document.getElementById(`source-${number}`)?.scrollIntoView({ behavior: 'smooth' });
  }

  protected async rate(rating: Rating): Promise<void> {
    const questionId = this.questionId();
    if (!questionId) {
      return;
    }
    try {
      await this.questionsApi.rate(questionId, rating);
      this.currentRating.set(rating);
      this.feedbackError.set(null);
    } catch (error) {
      this.feedbackError.set(describeApiError(error));
    }
  }
}
