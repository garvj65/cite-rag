export interface Citation {
  doc_id: string;
  page: number;
  quote: string;
  document_title: string;
  source: string;
  source_url: string | null;
  chunk_id: number;
  chunk_index: number;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  supported: boolean;
  reason: string;
  mode: 'model' | 'scripted' | 'no_model';
  verification: { proposed: number; valid: number };
}

export const MAX_QUERY_CHARACTERS = 2000;

/** Identify safe, user-facing failures without exposing arbitrary server or network text. */
export class ApiError extends Error {}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function integer(value: unknown, minimum: number): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= minimum;
}

function citation(value: unknown): Citation {
  if (!record(value) || typeof value.doc_id !== 'string' || !value.doc_id
    || !integer(value.page, 1) || typeof value.quote !== 'string' || !value.quote.trim()
    || typeof value.document_title !== 'string' || typeof value.source !== 'string'
    || !(value.source_url === null || typeof value.source_url === 'string')
    || !integer(value.chunk_id, 1) || !integer(value.chunk_index, 0)) {
    throw new ApiError('The server returned an invalid citation. Please try again.');
  }
  return {
    doc_id: value.doc_id, page: value.page, quote: value.quote,
    document_title: value.document_title, source: value.source, source_url: value.source_url,
    chunk_id: value.chunk_id, chunk_index: value.chunk_index,
  };
}

/** Check the response contract before displaying any answer text or quoted evidence. */
export function parseAnswer(value: unknown): AskResponse {
  const reasons = new Set(['supported', 'no_retrieval', 'weak_retrieval', 'context_limit',
    'model_unsupported', 'invalid_citations']);
  if (!record(value) || typeof value.answer !== 'string' || !value.answer.trim()
    || typeof value.supported !== 'boolean' || !Array.isArray(value.citations)
    || typeof value.reason !== 'string' || !reasons.has(value.reason)
    || !(value.mode === 'model' || value.mode === 'scripted' || value.mode === 'no_model')
    || !record(value.verification) || !integer(value.verification.proposed, 0)
    || !integer(value.verification.valid, 0)
    || value.verification.valid > value.verification.proposed) {
    throw new ApiError('The server returned an invalid answer. Please try again.');
  }
  const items: unknown[] = value.citations;
  const citations = items.map(citation);
  if ((value.supported && (citations.length === 0 || value.reason !== 'supported'
      || value.verification.valid !== value.verification.proposed
      || value.verification.valid < citations.length || value.mode === 'no_model'))
    || (!value.supported && (citations.length !== 0 || value.reason === 'supported'))) {
    throw new ApiError('The answer could not be verified. Please try again.');
  }
  return { answer: value.answer, citations, supported: value.supported, reason: value.reason,
    mode: value.mode, verification: {
      proposed: value.verification.proposed, valid: value.verification.valid,
    } };
}

/** Send one question through the same-origin proxy; model credentials stay on the server. */
export async function askQuestion(query: string, signal: AbortSignal): Promise<AskResponse> {
  const response = await fetch('/api/ask', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }), signal,
  });
  let payload: unknown;
  try { payload = await response.json(); }
  catch { throw new ApiError('The server returned an unreadable response. Please try again.'); }
  if (!response.ok) {
    const messages: Record<string, string> = {
      invalid_search_request: 'Check your question and try again.',
      provider_not_configured: 'The model provider needs to be configured on the server.',
      provider_timeout: 'The model took too long to respond. Please try again.',
      provider_failure: 'The model is temporarily unavailable. Please try again.',
      invalid_model_output: 'The model returned an invalid answer. Please try again.',
      database_unavailable: 'Document search is temporarily unavailable. Please try again.',
    };
    const code = record(payload) && record(payload.error) && typeof payload.error.code === 'string'
      ? payload.error.code : '';
    const message = Object.hasOwn(messages, code) ? messages[code] : undefined;
    throw new ApiError(message ?? 'We could not complete the request. Please try again.');
  }
  return parseAnswer(payload);
}
