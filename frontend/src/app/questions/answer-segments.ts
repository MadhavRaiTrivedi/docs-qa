export type AnswerSegment = { kind: 'text'; text: string } | { kind: 'citation'; number: number };

const CITATION = /\[(\d+(?:\s*,\s*\d+)*)\]/g;

/** Splits an answer into text and citation markers, so [2] can be shown as a link to source 2. */
export function splitCitations(answer: string, sourceCount: number): AnswerSegment[] {
  const segments: AnswerSegment[] = [];
  let position = 0;
  for (const match of answer.matchAll(CITATION)) {
    const numbers = match[1].split(',').map((part) => Number(part.trim()));
    if (!numbers.every((number) => number >= 1 && number <= sourceCount)) {
      continue;
    }
    if (match.index > position) {
      segments.push({ kind: 'text', text: answer.slice(position, match.index) });
    }
    segments.push(...numbers.map((number) => ({ kind: 'citation' as const, number })));
    position = match.index + match[0].length;
  }
  if (position < answer.length) {
    segments.push({ kind: 'text', text: answer.slice(position) });
  }
  return segments;
}
