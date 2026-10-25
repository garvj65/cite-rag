import type { AskResponse } from '../api/ask';

/** Offline UI fixture only; this is not a NIST golden evaluation question or answer. */
export const supportedAnswer: AskResponse = {
  answer: 'Keep the original document and record its source.', supported: true,
  reason: 'supported', mode: 'scripted', verification: { proposed: 1, valid: 1 },
  citations: [{ doc_id: 'a'.repeat(64), page: 2, quote: 'Keep the original document',
    document_title: 'Offline UI fixture', source: 'Test fixture',
    source_url: 'https://example.test/document.pdf', chunk_id: 1, chunk_index: 0 }],
};

/** Represent an evidence refusal with no generated claims or citations. */
export const refusalAnswer: AskResponse = {
  answer: "I couldn't find enough support for an answer in the documents.",
  supported: false, citations: [], reason: 'weak_retrieval', mode: 'no_model',
  verification: { proposed: 0, valid: 0 },
};
