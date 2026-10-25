import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { MAX_QUERY_CHARACTERS } from './api/ask';
import { supportedAnswer, refusalAnswer } from './test/fixtures';

describe('question-to-answer interface', (): void => {
  it('starts with an accessible empty state and no request', (): void => {
    const request = vi.fn();
    vi.stubGlobal('fetch', request);
    render(<App />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Answers with');
    expect(screen.getByRole('textbox', { name: 'What would you like to know?' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Find an answer' })).toBeDisabled();
    expect(screen.getByText('Every answer starts with a source.')).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });

  it('shows loading, then a supported answer and expandable source card', async (): Promise<void> => {
    let resolve: (value: Response) => void = (): void => { throw new Error('Request not started'); };
    const request = vi.fn<typeof fetch>((): Promise<Response> => new Promise((done): void => { resolve = done; }));
    vi.stubGlobal('fetch', request);
    render(<App />);
    const user = userEvent.setup();
    await user.type(screen.getByRole('textbox'), 'What should I retain?');
    await user.click(screen.getByRole('button', { name: 'Find an answer' }));
    expect(screen.getByRole('status')).toHaveTextContent('Retrieving passages');
    expect(screen.getByRole('textbox')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Checking evidence…' })).toBeDisabled();
    resolve(new Response(JSON.stringify(supportedAnswer)));
    expect(await screen.findByText(supportedAnswer.answer)).toBeVisible();
    expect(screen.getByText('Scripted demo response')).toBeVisible();
    expect(screen.getByText('Keep the original document', { selector: 'blockquote' })).not.toBeVisible();
    await user.click(screen.getByText('Offline UI fixture'));
    expect(screen.getByText('Keep the original document', { selector: 'blockquote' })).toBeVisible();
    expect(screen.getByRole('link', { name: 'Open document ↗' })).toHaveAttribute('href',
      'https://example.test/document.pdf#page=2');
    expect(request).toHaveBeenCalledTimes(1);
    expect(request.mock.calls[0]?.[0]).toBe('/api/ask');
  });

  it('shows a refusal without source cards', async (): Promise<void> => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(refusalAnswer))));
    render(<App />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Unsupported question' } });
    fireEvent.submit(screen.getByRole('textbox').closest('form')!);
    expect(await screen.findByText(refusalAnswer.answer)).toBeVisible();
    expect(screen.getByText('An answer couldn’t be verified.')).toBeVisible();
    expect(screen.queryByRole('region', { name: 'Verified citations' })).not.toBeInTheDocument();
  });

  it('shows sanitized server errors and permits another attempt', async (): Promise<void> => {
    const request = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { code: 'provider_timeout', message: 'private provider text' },
    }), { status: 504 }));
    vi.stubGlobal('fetch', request);
    render(<App />);
    const user = userEvent.setup();
    await user.type(screen.getByRole('textbox'), 'A question');
    await user.click(screen.getByRole('button', { name: 'Find an answer' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The model took too long');
    expect(screen.queryByText('private provider text')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Find an answer' })).toBeEnabled();
  });

  it('handles connection failures and malformed answer payloads', async (): Promise<void> => {
    const request = vi.fn().mockRejectedValueOnce(new TypeError('private network detail'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ answer: 'Uncited claim', supported: true })));
    vi.stubGlobal('fetch', request);
    render(<App />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'A question' } });
    const submit = screen.getByRole('button', { name: 'Find an answer' });
    fireEvent.click(submit);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to reach CiteRAG');
    fireEvent.click(submit);
    await waitFor((): void => { expect(screen.getByRole('alert')).toHaveTextContent('invalid answer'); });
    expect(screen.queryByText('Uncited claim')).not.toBeInTheDocument();
  });

  it('rejects whitespace and oversized questions without making a request', async (): Promise<void> => {
    const request = vi.fn();
    vi.stubGlobal('fetch', request);
    render(<App />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.submit(input.closest('form')!);
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter a question');
    fireEvent.change(input, { target: { value: 'x'.repeat(MAX_QUERY_CHARACTERS + 1) } });
    fireEvent.submit(input.closest('form')!);
    expect(await screen.findByRole('alert')).toHaveTextContent('2,000 characters');
    expect(request).not.toHaveBeenCalled();
  });

  it('renders answer and quote text as text rather than executable HTML', async (): Promise<void> => {
    const unsafe = '<img src=x onerror=alert(1)>';
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      ...supportedAnswer, answer: unsafe,
      citations: [{ ...supportedAnswer.citations[0], quote: '<script>alert(1)</script>',
        source_url: 'javascript:alert(1)' }],
    }))));
    const { container } = render(<App />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'A question' } });
    fireEvent.click(screen.getByRole('button', { name: 'Find an answer' }));
    expect(await screen.findByText(unsafe)).toBeVisible();
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('script')).toBeNull();
    expect(screen.queryByRole('link', { name: 'Open document ↗' })).not.toBeInTheDocument();
  });

  it('clears the previous answer when the question is edited', async (): Promise<void> => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(supportedAnswer))));
    render(<App />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'First question' } });
    fireEvent.click(screen.getByRole('button', { name: 'Find an answer' }));
    expect(await screen.findByText(supportedAnswer.answer)).toBeVisible();
    fireEvent.change(input, { target: { value: 'A different question' } });
    expect(screen.queryByText(supportedAnswer.answer)).not.toBeInTheDocument();
  });

  it('aborts a pending request on unmount', async (): Promise<void> => {
    const request = vi.fn().mockReturnValue(new Promise<Response>((): void => {}));
    vi.stubGlobal('fetch', request);
    const { unmount } = render(<App />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'A question' } });
    fireEvent.click(screen.getByRole('button', { name: 'Find an answer' }));
    await waitFor((): void => expect(request).toHaveBeenCalled());
    const options = request.mock.calls[0]?.[1] as RequestInit;
    unmount();
    expect(options.signal?.aborted).toBe(true);
  });
});
