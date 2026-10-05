import { splitCitations } from './answer-segments';

describe('splitCitations', () => {
  it('turns markers into citation segments', () => {
    expect(splitCitations('Twelve days [1]. Paid [1, 2].', 2)).toEqual([
      { kind: 'text', text: 'Twelve days ' },
      { kind: 'citation', number: 1 },
      { kind: 'text', text: '. Paid ' },
      { kind: 'citation', number: 1 },
      { kind: 'citation', number: 2 },
      { kind: 'text', text: '.' },
    ]);
  });

  it('keeps markers that point at no source as text', () => {
    expect(splitCitations('See [7].', 2)).toEqual([{ kind: 'text', text: 'See [7].' }]);
  });
});
