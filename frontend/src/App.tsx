import { useEffect, useRef, useState, type FormEvent, type ReactElement } from 'react';
import { ApiError, askQuestion, MAX_QUERY_CHARACTERS, type AskResponse } from './api/ask';
import { CitationCard } from './components/CitationCard';

/** Present one evidence-backed answer at a time, with clear loading, refusal, and error states. */
export function App(): ReactElement {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const activeRequest = useRef<AbortController | null>(null);

  useEffect(() => (): void => activeRequest.current?.abort(), []);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (loading) return;
    const query = question.trim();
    if (!query || query.length > MAX_QUERY_CHARACTERS) {
      setError(`Enter a question of up to ${MAX_QUERY_CHARACTERS.toLocaleString('en-US')} characters.`);
      return;
    }
    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await askQuestion(query, controller.signal);
      if (!controller.signal.aborted) setResult(response);
    } catch (failure: unknown) {
      if (!controller.signal.aborted) setError(failure instanceof ApiError ? failure.message
        : 'Unable to reach CiteRAG. Check your connection and try again.');
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="wordmark" href="/" aria-label="CiteRAG home"><span className="brand-mark" aria-hidden="true">c<span>↗</span></span>Cite<span>RAG</span></a>
        <span className="header-note"><span className="status-dot" />DOCUMENT-GROUNDED ANSWERS</span>
      </header>

      <main>
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow">LESS GUESSWORK. MORE EVIDENCE.</p>
          <h1 id="page-title">Answers with<br />a <span>paper trail.</span></h1>
          <p className="intro-copy">Ask your documents a question.<br className="desktop-break" /> Get an answer with passages you can check.</p>
          <div className="principles" aria-label="How CiteRAG works">
            <span><b>01</b> Find the evidence</span>
            <span><b>02</b> Check every quote</span>
            <span><b>03</b> Show the source</span>
          </div>
        </section>

        <section className="workspace" aria-label="Ask your documents">
          <form className="question-panel" onSubmit={(event): void => { void submit(event); }}>
            <div className="panel-heading"><label htmlFor="question">What would you like to know?</label><span className="small-label">YOUR QUESTION</span></div>
            <textarea id="question" name="question" rows={4} value={question}
              onChange={(event): void => { setQuestion(event.target.value); setResult(null); setError(null); }}
              placeholder="Ask about something in your documents…" disabled={loading}
              maxLength={MAX_QUERY_CHARACTERS} aria-describedby="question-help" />
            <div className="question-actions">
              <span id="question-help" className="question-help">{question.length.toLocaleString('en-US')} / {MAX_QUERY_CHARACTERS.toLocaleString('en-US')} characters</span>
              <button type="submit" disabled={loading || !question.trim()}>
                {loading ? 'Checking evidence…' : 'Find an answer'}<span aria-hidden="true">↗</span>
              </button>
            </div>
          </form>

          <div className="result-area" aria-live="polite" aria-busy={loading}>
            {loading && <div className="loading-state" role="status"><span className="spinner" aria-hidden="true" />Retrieving passages and checking citations…</div>}
            {error && <div className="error-state" role="alert"><strong>Something needs another try.</strong><p>{error}</p></div>}
            {result && <article className={`answer-panel ${result.supported ? '' : 'refusal-panel'}`}>
              <div className="answer-topline"><span className="eyebrow">{result.supported ? 'THE ANSWER' : 'NOT ENOUGH EVIDENCE'}</span>
                {result.mode === 'scripted' && <span className="demo-label">Scripted demo response</span>}
              </div>
              <h2>{result.supported ? 'Here’s what the documents support.' : 'An answer couldn’t be verified.'}</h2>
              <p className="answer-text">{result.answer}</p>
              {result.supported && <section className="citations" aria-label="Verified citations">
                <div className="sources-heading"><h3>Follow the evidence</h3><span>{result.citations.length} verified {result.citations.length === 1 ? 'passage' : 'passages'}</span></div>
                {result.citations.map((citation, index) => <CitationCard key={`${citation.chunk_id}-${index}`} citation={citation} number={index + 1} />)}
                <p className="verification-note">Quotes are matched to retrieved passages. Open the source to assess the answer in context.</p>
              </section>}
            </article>}
            {!loading && !error && !result && <div className="empty-state">
              <span className="quote-mark" aria-hidden="true">“</span>
              <h2>Every answer starts with a source.</h2>
              <p>Verified quotes will appear here with the document and PDF page.<br />When the evidence is missing, CiteRAG will say so.</p>
            </div>}
          </div>
        </section>
      </main>

      <footer><span>Built around evidence.</span><span>Read the quote. Check the context.</span></footer>
    </div>
  );
}
