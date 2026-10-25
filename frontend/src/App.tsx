import { useEffect, useRef, useState, type FormEvent, type ReactElement } from 'react';
import {
  ApiError,
  askQuestion,
  characterCount,
  loadClientConfig,
  type AskResponse,
  type ClientConfig,
  type RetrievalStrategy,
  type SearchOptions,
} from './api/ask';
import { CitationCard } from './components/CitationCard';

const STRATEGIES: { id: RetrievalStrategy; label: string; description: string }[] = [
  { id: 'hybrid', label: 'Hybrid', description: 'Combine meaning and keyword matches.' },
  { id: 'vector', label: 'Vector', description: 'Find passages by similarity in meaning.' },
  {
    id: 'keyword',
    label: 'Keyword',
    description: 'Find passages with matching words and phrases.',
  },
];

/** Provide one research workspace with backend-owned controls and checked citation evidence. */
export function App(): ReactElement {
  const [config, setConfig] = useState<ClientConfig | null>(null);
  const [selection, setSelection] = useState<SearchOptions | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const activeRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setConfig(null);
    setConfigError(null);
    void loadClientConfig(controller.signal)
      .then((value): void => {
        if (!controller.signal.aborted) {
          setConfig(value);
          setSelection({ strategy: value.search_strategy, k: value.search_k });
        }
      })
      .catch((failure: unknown): void => {
        if (!controller.signal.aborted)
          setConfigError(
            failure instanceof ApiError
              ? failure.message
              : 'Unable to load workspace settings. Check your connection and try again.',
          );
      });
    return (): void => controller.abort();
  }, [revision]);
  useEffect(() => (): void => activeRequest.current?.abort(), []);

  function clearAnswer(): void {
    setResult(null);
    setError(null);
  }
  const count = characterCount(question.trim());
  const tooLong = config !== null && count > config.max_query_characters;
  const ready = config !== null && selection !== null;
  const strategy = STRATEGIES.find((item) => item.id === selection?.strategy);
  const sources = new Set(result?.citations.map((citation) => citation.doc_id)).size;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (activeRequest.current) return;
    if (!config || !selection) return;
    const query = question.trim();
    if (!query || characterCount(query) > config.max_query_characters) {
      setError(
        `Enter a question of up to ${config.max_query_characters.toLocaleString('en-US')} characters.`,
      );
      return;
    }
    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const answer = await askQuestion(query, controller.signal, selection);
      if (!controller.signal.aborted) setResult(answer);
    } catch (failure: unknown) {
      if (!controller.signal.aborted)
        setError(
          failure instanceof ApiError
            ? failure.message
            : 'Unable to reach CiteRAG. Check your connection and try again.',
        );
    } finally {
      if (activeRequest.current === controller) activeRequest.current = null;
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#research">
        Skip to research
      </a>
      <aside className="sidebar" aria-label="Workspace navigation">
        <a className="wordmark" href="/" aria-label="CiteRAG home">
          <span className="brand-mark" aria-hidden="true">
            c<span>↗</span>
          </span>
          <span>
            Cite<span className="brand-light">RAG</span>
          </span>
        </a>
        <div className="workspace-label">
          YOUR WORKSPACE <span>01</span>
        </div>
        <nav aria-label="Research">
          <a className="nav-item" href="#research" aria-current="page">
            <span aria-hidden="true">⌕</span>Research desk
            <span className="nav-arrow" aria-hidden="true">
              ↗
            </span>
          </a>
        </nav>
        <div className="sidebar-note">
          <span className="small-label">BUILT FOR THE FOOTNOTES</span>
          <p>A good answer gives you somewhere to look.</p>
          <span className="note-rule" />
        </div>
        <details className="methodology">
          <summary>
            <span className="help-icon" aria-hidden="true">
              ?
            </span>
            How it works<span aria-hidden="true">+</span>
          </summary>
          <div>
            <p>
              CiteRAG finds relevant passages, asks a model to answer from them, then checks each
              quote against its source.
            </p>
            <p>
              If evidence or citation checks fail, it withholds the answer. A matching quote proves
              where the words came from; read its context to assess the claim.
            </p>
          </div>
        </details>
        <div className="sidebar-footer">
          <span className="tiny-mark" aria-hidden="true">
            ↳
          </span>{' '}
          Evidence over guesswork.
        </div>
      </aside>

      <div className="main-shell">
        <header className="workspace-header">
          <div>
            <span className="header-slash" aria-hidden="true">
              /
            </span>{' '}
            RESEARCH DESK
          </div>
          <span className="policy-badge">
            <span aria-hidden="true">✳</span>Citations required
          </span>
        </header>
        <main id="research" className="research" tabIndex={-1}>
          <section className="intro" aria-labelledby="page-title">
            <p className="eyebrow">
              <span /> A LITTLE MORE CERTAINTY
            </p>
            <h1 id="page-title">
              Good questions.
              <br />
              <span>Better evidence.</span>
            </h1>
            <p className="intro-copy">
              Explore your documents. Trace the answer.
              <br className="desktop-break" /> Keep the source within reach.
            </p>
          </section>

          <section className="question-panel" aria-label="Ask your documents">
            <form
              onSubmit={(event): void => {
                void submit(event);
              }}
            >
              <div className="panel-heading">
                <label htmlFor="question">Your research question</label>
                <span className="question-index" aria-hidden="true">
                  Q / 01
                </span>
              </div>
              <textarea
                id="question"
                name="question"
                rows={3}
                value={question}
                onChange={(event): void => {
                  setQuestion(event.target.value);
                  clearAnswer();
                }}
                placeholder="What would you like to understand?"
                disabled={!ready || loading}
                // HTML counts UTF-16 units; enforce the backend's code-point limit separately.
                maxLength={config ? config.max_query_characters * 2 : undefined}
                aria-invalid={tooLong}
                aria-describedby="question-help retrieval-help"
              />
              <div className="question-toolbar">
                <fieldset className="strategy-switch" disabled={!ready || loading}>
                  <legend>Retrieval strategy</legend>
                  {STRATEGIES.map((item) => (
                    <button
                      type="button"
                      key={item.id}
                      aria-pressed={selection?.strategy === item.id}
                      onClick={(): void => {
                        setSelection((current) =>
                          current ? { ...current, strategy: item.id } : null,
                        );
                        clearAnswer();
                      }}
                    >
                      {item.label}
                    </button>
                  ))}
                </fieldset>
                <label className="passage-control">
                  Passages
                  <select
                    aria-label="Passages to retrieve"
                    value={selection?.k ?? ''}
                    disabled={!ready || loading}
                    onChange={(event): void => {
                      const k = Number(event.target.value);
                      setSelection((current) => (current ? { ...current, k } : null));
                      clearAnswer();
                    }}
                  >
                    {!config && <option value="">—</option>}
                    {config &&
                      Array.from({ length: config.search_max_k }, (_, index) => index + 1).map(
                        (k) => (
                          <option value={k} key={k}>
                            {k}
                          </option>
                        ),
                      )}
                  </select>
                  <span aria-hidden="true">⌄</span>
                </label>
                <button
                  className="submit-button"
                  type="submit"
                  disabled={!ready || loading || !question.trim() || tooLong}
                >
                  {loading ? 'Checking evidence…' : 'Find an answer'}
                  <span aria-hidden="true">↗</span>
                </button>
              </div>
              <div className="form-notes">
                <span id="retrieval-help">
                  {strategy?.description ?? 'Loading your workspace settings…'}
                </span>
                <span id="question-help" className={tooLong ? 'over-limit' : ''}>
                  {config
                    ? `${count.toLocaleString('en-US')} / ${config.max_query_characters.toLocaleString('en-US')} characters`
                    : 'Preparing controls'}
                </span>
              </div>
            </form>
            {!ready && !configError && (
              <p className="config-status" role="status">
                Preparing the workspace…
              </p>
            )}
            {configError && (
              <div className="config-error" role="alert">
                <p>{configError}</p>
                <button type="button" onClick={(): void => setRevision((value) => value + 1)}>
                  Retry loading settings <span aria-hidden="true">↗</span>
                </button>
              </div>
            )}
          </section>

          <section
            className="result-area"
            aria-label="Research result"
            aria-live="polite"
            aria-busy={loading}
          >
            {loading && (
              <div className="loading-state" role="status">
                <span className="loader-orbit" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
                <div>
                  <h2>Following the evidence.</h2>
                  <p>Finding passages and checking citations…</p>
                </div>
                <div className="skeleton-lines" aria-hidden="true">
                  <span />
                  <span />
                </div>
              </div>
            )}
            {error && (
              <div className="error-state" role="alert">
                <span className="state-icon" aria-hidden="true">
                  !
                </span>
                <div>
                  <p className="eyebrow">REQUEST INTERRUPTED</p>
                  <h2>Let’s try that again.</h2>
                  <p>{error}</p>
                </div>
              </div>
            )}
            {result && result.supported && (
              <div className="answer-layout">
                <article className="answer-panel">
                  <div className="answer-topline">
                    <p className="eyebrow">
                      <span className="answer-dot" />
                      THE ANSWER
                    </p>
                    {result.mode === 'scripted' && (
                      <span className="demo-label">Scripted demo response</span>
                    )}
                  </div>
                  <h2>Here’s what the documents support.</h2>
                  <p className="answer-text">{result.answer}</p>
                  <div className="answer-footer">
                    <span aria-hidden="true">↳</span>
                    <p>
                      Quotes are matched to retrieved passages.
                      <br />
                      Read the source to assess the answer in context.
                    </p>
                  </div>
                </article>
                <aside className="source-rail" aria-label="Verified citations">
                  <div className="sources-heading">
                    <h3>The paper trail</h3>
                    <span>
                      {sources} {sources === 1 ? 'source' : 'sources'} · {result.citations.length}{' '}
                      {result.citations.length === 1 ? 'passage' : 'passages'}
                    </span>
                  </div>
                  {result.citations.map((citation, index) => (
                    <CitationCard
                      key={`${citation.chunk_id}-${index}`}
                      citation={citation}
                      number={index + 1}
                    />
                  ))}
                </aside>
              </div>
            )}
            {result && !result.supported && (
              <article className="refusal-panel">
                <span className="state-icon" aria-hidden="true">
                  ↳
                </span>
                <div>
                  <div className="answer-topline">
                    <p className="eyebrow">NOT ENOUGH EVIDENCE</p>
                    {result.mode === 'scripted' && (
                      <span className="demo-label">Scripted demo response</span>
                    )}
                  </div>
                  <h2>No answer without evidence.</h2>
                  <p className="answer-text">{result.answer}</p>
                  <p className="refusal-tip">
                    Try a more specific question or a different retrieval strategy.
                  </p>
                </div>
              </article>
            )}
            {!loading && !error && !result && (
              <div className="empty-state">
                <div className="paper-symbol" aria-hidden="true">
                  <div className="paper-back" />
                  <div className="paper-front">
                    <span>“</span>
                    <i />
                    <i />
                    <i />
                  </div>
                  <span className="paper-star">✳</span>
                </div>
                <div className="empty-copy">
                  <p className="small-label">READY WHEN YOU ARE</p>
                  <h2>
                    Every insight starts
                    <br />
                    with something you can check.
                  </h2>
                  <p>
                    Your answer will arrive with exact quotes, document names,
                    <br className="desktop-break" /> and PDF pages. No supporting evidence? We’ll
                    say so.
                  </p>
                </div>
                <div className="evidence-steps">
                  <span>
                    <b>01</b>Find the passage
                  </span>
                  <span>
                    <b>02</b>Check the quote
                  </span>
                  <span>
                    <b>03</b>Follow the source
                  </span>
                </div>
              </div>
            )}
          </section>
          <footer className="page-footer">
            <span>Curiosity, with receipts.</span>
            <span>
              CiteRAG <span aria-hidden="true">↗</span>
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
