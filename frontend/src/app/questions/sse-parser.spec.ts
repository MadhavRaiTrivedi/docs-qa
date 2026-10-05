import { SseParser } from './sse-parser';

describe('SseParser', () => {
  it('parses complete events', () => {
    const events = new SseParser().push('event: delta\ndata: {"text":"Hi"}\n\n');

    expect(events).toEqual([{ name: 'delta', data: '{"text":"Hi"}' }]);
  });

  it('waits for the rest of an event split across chunks', () => {
    const parser = new SseParser();

    const first = parser.push('event: delta\ndata: {"te');
    const second = parser.push('xt":"Hi"}\n\nevent: done\ndata: {}\n\n');

    expect(first).toEqual([]);
    expect(second.map((event) => event.name)).toEqual(['delta', 'done']);
  });

  it('defaults the event name to message', () => {
    expect(new SseParser().push('data: x\n\n')).toEqual([{ name: 'message', data: 'x' }]);
  });
});
