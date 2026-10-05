export interface ServerSentEvent {
  name: string;
  data: string;
}

/** Splits a text/event-stream into events. Network chunks can end mid-line, so input is buffered. */
export class SseParser {
  private buffer = '';

  push(chunk: string): ServerSentEvent[] {
    this.buffer += chunk;
    const blocks = this.buffer.split('\n\n');
    this.buffer = blocks.pop() ?? '';
    return blocks.map(SseParser.parseBlock).filter((event) => event.data !== '');
  }

  private static parseBlock(block: string): ServerSentEvent {
    let name = 'message';
    const data: string[] = [];
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) {
        name = line.slice('event:'.length).trim();
      } else if (line.startsWith('data:')) {
        data.push(line.slice('data:'.length).trimStart());
      }
    }
    return { name, data: data.join('\n') };
  }
}
