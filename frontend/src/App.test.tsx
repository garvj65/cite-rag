import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { App } from './App';
import type { ClientConfig } from './api/ask';
import { clientConfig, supportedAnswer, refusalAnswer } from './test/fixtures';

function mockRequests(
  answer: () => Promise<Response> = async () => new Response(JSON.stringify(supportedAnswer)),
  config: ClientConfig = clientConfig,
) {
  const request = vi.fn<typeof fetch>(async (url) => {
    if (url === '/api/config') return new Response(JSON.stringify(config));
    if (url === '/api/ask') return answer();
    throw new Error('Unexpected request');
  });
  vi.stubGlobal('fetch', request);
  return request;
}
async function ready(): Promise<HTMLElement> {
  const input = screen.getByRole('textbox', { name: 'Your research question' });
  await waitFor((): void => {
    expect(input).toBeEnabled();
  });
  return input;
}
async function submitQuestion(text = 'A synthetic question'): Promise<void> {
  fireEvent.change(await ready(), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: 'Find an answer' }));
}

describe('research workspace', (): void => {
  it('waits for authoritative settings before enabling controls', async (): Promise<void> => {
    let resolve: (value: Response) => void = (): void => {
      throw new Error('Not requested');
    };
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(
        (): Promise<Response> =>
          new Promise((done): void => {
            resolve = done;
          }),
      ),
    );
    render(<App />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Good questions.');
    expect(screen.getByRole('textbox')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Find an answer' })).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('Preparing the workspace');
    resolve(new Response(JSON.stringify(clientConfig)));
    await ready();
    expect(screen.getByRole('button', { name: 'Hybrid' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('link', { name: 'Skip to research' })).toHaveAttribute(
      'href',
      '#research',
    );
  });
  it('shows loading then an answer and expandable exact quote', async (): Promise<void> => {
    let resolve: (value: Response) => void = (): void => {
      throw new Error('Not requested');
    };
    const request = mockRequests(
      (): Promise<Response> =>
        new Promise((done): void => {
          resolve = done;
        }),
    );
    render(<App />);
    await submitQuestion();
    expect(screen.getByRole('status')).toHaveTextContent('Following the evidence');
    expect(screen.getByRole('textbox')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Hybrid' })).toBeDisabled();
    resolve(new Response(JSON.stringify(supportedAnswer)));
    expect(await screen.findByText(supportedAnswer.answer)).toBeVisible();
    expect(screen.getByText('Scripted demo response')).toBeVisible();
    expect(
      screen.getByText('Keep the original document', { selector: 'blockquote' }),
    ).not.toBeVisible();
    await userEvent.click(screen.getByText('Offline UI fixture'));
    expect(
      screen.getByText('Keep the original document', { selector: 'blockquote' }),
    ).toBeVisible();
    expect(screen.getByRole('link', { name: 'Open document ↗' })).toHaveAttribute(
      'href',
      'https://example.test/document.pdf#page=2',
    );
    const calls = request.mock.calls.filter(([url]) => url === '/api/ask');
    expect(calls).toHaveLength(1);
    expect(JSON.parse(String(calls[0]?.[1]?.body))).toEqual({
      query: 'A synthetic question',
      strategy: 'hybrid',
      k: 5,
    });
  });
  it('uses backend defaults and sends changed strategy and k', async (): Promise<void> => {
    const request = mockRequests(undefined, {
      ...clientConfig,
      search_strategy: 'keyword',
      search_k: 2,
      search_max_k: 7,
    });
    render(<App />);
    await ready();
    expect(screen.getByRole('button', { name: 'Keyword' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('combobox')).toHaveValue('2');
    await userEvent.click(screen.getByRole('button', { name: 'Vector' }));
    await userEvent.selectOptions(screen.getByRole('combobox'), '7');
    await submitQuestion();
    await screen.findByText(supportedAnswer.answer);
    const call = request.mock.calls.find(([url]) => url === '/api/ask');
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
      query: 'A synthetic question',
      strategy: 'vector',
      k: 7,
    });
  });
  it('shows a refusal without citation cards', async (): Promise<void> => {
    mockRequests(async () => new Response(JSON.stringify(refusalAnswer)));
    const { container } = render(<App />);
    await submitQuestion();
    expect(await screen.findByText(refusalAnswer.answer)).toBeVisible();
    expect(screen.getByText('No answer without evidence.')).toBeVisible();
    expect(container.querySelectorAll('.citation-card')).toHaveLength(0);
  });
  it('sanitizes provider and deadline errors and permits retry', async (): Promise<void> => {
    const answer = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ error: { code: 'provider_timeout', message: 'private provider body' } }),
          { status: 504 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ error: { code: 'request_timeout', message: 'private deadline body' } }),
          { status: 504 },
        ),
      );
    mockRequests(answer);
    render(<App />);
    await submitQuestion();
    expect(await screen.findByRole('alert')).toHaveTextContent('The model took too long');
    expect(screen.queryByText('private provider body')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Find an answer' }));
    await waitFor((): void => {
      expect(screen.getByRole('alert')).toHaveTextContent('The request took too long');
    });
    expect(screen.getByRole('button', { name: 'Find an answer' })).toBeEnabled();
  });
  it('handles connection failures and malformed answer contracts', async (): Promise<void> => {
    const answer = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('private network detail'))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ answer: 'Uncited claim', supported: true })),
      );
    mockRequests(answer);
    render(<App />);
    await submitQuestion();
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to reach CiteRAG');
    fireEvent.click(screen.getByRole('button', { name: 'Find an answer' }));
    await waitFor((): void => {
      expect(screen.getByRole('alert')).toHaveTextContent('invalid answer');
    });
    expect(screen.queryByText('Uncited claim')).not.toBeInTheDocument();
  });
  it('enforces nondefault limits using Unicode code points', async (): Promise<void> => {
    const request = mockRequests(undefined, { ...clientConfig, max_query_characters: 3 });
    render(<App />);
    const input = await ready();
    fireEvent.change(input, { target: { value: 'abcd' } });
    expect(screen.getByText('4 / 3 characters')).toBeVisible();
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('button', { name: 'Find an answer' })).toBeDisabled();
    fireEvent.submit(input.closest('form')!);
    expect(await screen.findByRole('alert')).toHaveTextContent('up to 3 characters');
    expect(request.mock.calls.filter(([url]) => url === '/api/ask')).toHaveLength(0);
    fireEvent.change(input, { target: { value: '😀😀😀' } });
    expect(screen.getByText('3 / 3 characters')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Find an answer' }));
    await screen.findByText(supportedAnswer.answer);
    expect(
      JSON.parse(String(request.mock.calls.find(([url]) => url === '/api/ask')?.[1]?.body)).query,
    ).toBe('😀😀😀');
  });
  it('rejects whitespace without a model request', async (): Promise<void> => {
    const request = mockRequests();
    render(<App />);
    const input = await ready();
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.submit(input.closest('form')!);
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter a question');
    expect(request.mock.calls.filter(([url]) => url === '/api/ask')).toHaveLength(0);
  });
  it('renders HTML-looking content as text and blocks unsafe source links', async (): Promise<void> => {
    const unsafe = '<img src=x onerror=alert(1)>';
    mockRequests(
      async () =>
        new Response(
          JSON.stringify({
            ...supportedAnswer,
            answer: unsafe,
            citations: [
              {
                ...supportedAnswer.citations[0],
                quote: '<script>alert(1)</script>',
                source_url: 'javascript:alert(1)',
              },
            ],
          }),
        ),
    );
    const { container } = render(<App />);
    await submitQuestion();
    expect(await screen.findByText(unsafe)).toBeVisible();
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('script')).toBeNull();
    expect(screen.queryByRole('link', { name: 'Open document ↗' })).not.toBeInTheDocument();
  });
  it('clears stale answers on question and strategy changes', async (): Promise<void> => {
    mockRequests();
    render(<App />);
    await submitQuestion();
    await screen.findByText(supportedAnswer.answer);
    await userEvent.click(screen.getByRole('button', { name: 'Keyword' }));
    expect(screen.queryByText(supportedAnswer.answer)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Find an answer' }));
    await screen.findByText(supportedAnswer.answer);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Changed question' } });
    expect(screen.queryByText(supportedAnswer.answer)).not.toBeInTheDocument();
  });
  it('blocks submissions after settings failure and retries without a fallback', async (): Promise<void> => {
    const request = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response('private', { status: 503 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...clientConfig, max_query_characters: 37 })),
      );
    vi.stubGlobal('fetch', request);
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Workspace settings are temporarily unavailable',
    );
    expect(screen.getByRole('textbox')).toBeDisabled();
    fireEvent.submit(screen.getByRole('textbox').closest('form')!);
    expect(request).toHaveBeenCalledTimes(1);
    await userEvent.click(screen.getByRole('button', { name: 'Retry loading settings' }));
    await ready();
    expect(screen.getByText('0 / 37 characters')).toBeVisible();
    expect(request).toHaveBeenCalledTimes(2);
  });
  it('aborts active answer requests on unmount', async (): Promise<void> => {
    const request = mockRequests(() => new Promise<Response>((): void => {}));
    const { unmount } = render(<App />);
    await submitQuestion();
    const options = request.mock.calls.find(([url]) => url === '/api/ask')?.[1] as RequestInit;
    unmount();
    expect(options.signal?.aborted).toBe(true);
  });
});
