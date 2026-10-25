import { describe, expect, it, vi } from 'vitest';
import { askQuestion, parseAnswer } from './ask';
import { refusalAnswer, supportedAnswer } from '../test/fixtures';

describe('answer response validation', (): void => {
  it('does not use inherited properties as server error messages', async (): Promise<void> => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { code: '__proto__', message: 'private text' },
    }), { status: 500 })));
    await expect(askQuestion('question', new AbortController().signal)).rejects.toThrow(
      'We could not complete the request',
    );
  });
  it('accepts complete supported and refused responses', (): void => {
    expect(parseAnswer(supportedAnswer)).toEqual(supportedAnswer);
    expect(parseAnswer(refusalAnswer)).toEqual(refusalAnswer);
  });

  it.each([
    {}, { ...supportedAnswer, citations: [] }, { ...supportedAnswer, supported: 'true' },
    { ...supportedAnswer, mode: 'no_model' }, { ...supportedAnswer, reason: 'invented' },
    { ...supportedAnswer, verification: { proposed: 0, valid: 1 } },
    { ...supportedAnswer, verification: { proposed: 2, valid: 1 } },
    { ...supportedAnswer, citations: [{ ...supportedAnswer.citations[0], page: 0 }] },
    { ...supportedAnswer, citations: [{ ...supportedAnswer.citations[0], quote: '' }] },
    { ...refusalAnswer, citations: supportedAnswer.citations },
  ])('rejects an inconsistent or malformed response', (value: unknown): void => {
    expect((): void => { parseAnswer(value); }).toThrow();
  });

  it('rejects non-JSON bodies and does not expose unknown error text', async (): Promise<void> => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response('<html>proxy error</html>'))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        error: { code: 'unknown_error', message: 'private server detail' },
      }), { status: 500 })));
    const signal = new AbortController().signal;
    await expect(askQuestion('question', signal)).rejects.toThrow('unreadable response');
    await expect(askQuestion('question', signal)).rejects.toThrow('We could not complete');
  });
});
