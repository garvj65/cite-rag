import type { ReactElement } from 'react';
import type { Citation } from '../api/ask';

function sourceLink(citation: Citation): string | null {
  if (!citation.source_url) return null;
  try {
    const url = new URL(citation.source_url);
    if (!['https:', 'http:'].includes(url.protocol)) return null;
    url.hash = `page=${citation.page}`;
    return url.toString();
  } catch {
    return null;
  }
}

/** Show an exact verified quote and a document link without rendering document HTML. */
export function CitationCard({
  citation,
  number,
}: {
  citation: Citation;
  number: number;
}): ReactElement {
  const link = sourceLink(citation);
  return (
    <details className="citation-card">
      <summary>
        <span className="citation-number">{String(number).padStart(2, '0')}</span>
        <span className="citation-title">
          {citation.document_title}
          <span>PDF page {citation.page}</span>
        </span>
        <span className="expand-icon" aria-hidden="true">
          +
        </span>
      </summary>
      <div className="citation-body">
        <blockquote>{citation.quote}</blockquote>
        <div className="citation-source">
          <span>{citation.source}</span>
          {link && (
            <a href={link} target="_blank" rel="noopener noreferrer">
              Open document ↗
            </a>
          )}
        </div>
        <span className="quote-check">✓ QUOTE MATCHED TO SOURCE</span>
      </div>
    </details>
  );
}
