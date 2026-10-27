# Golden benchmark review

Version: 2026-10-26. Assistant-authored at the user's explicit request: 30 questions, 25
answerable and 5 unanswerable. q01–q05 preserve the original pilot. Labels and reference answers
were established from the fixed PDFs, independently of CiteRAG outputs. The user confirmed reviewing the answer key on 2026-10-27 and retained q30 as an
ambiguous false-premise edge case with its expected-refusal label. Golden bytes
and references remain unchanged. This is a small, non-random baseline over two publications, not a representative
production-quality estimate.

Only two answerable entries require multiple pages: q16 spans two RMF pages; q26 compares the
two documents. The remaining entries have one canonical gold page. Reference answers support
human review; no automatic semantic-answer or faithfulness judge is implemented.

## Questions and answer key

| ID | Question | Reference answer / expected behavior | Gold pages |
|---|---|---|---|
| q01 | What should accompany an AI system's accuracy measurements, according to the AI Risk Management Framework? | Clearly defined, realistic test sets representative of expected use, plus details of the test methodology in the documentation. | [RMF 19](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=19) |
| q02 | At what stage should AI safety considerations begin, according to the AI Risk Management Framework? | As early as possible, during planning and design, with safety considered throughout the lifecycle. | [RMF 20](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=20) |
| q03 | Besides false content, what two kinds of inconsistency does the Generative AI Profile include under confabulation? | Outputs that diverge from the prompt or input, and outputs that contradict earlier statements in the same context. | [GenAI 10](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=10) |
| q04 | Which two model-size reduction methods does the Generative AI Profile mention for reducing environmental impacts during inference? | Model distillation and compression; training and tuning these smaller models may still contribute environmental impacts. | [GenAI 12](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=12) |
| q05 | How many confirmed AI safety incidents worldwide in calendar year 2025 are reported in these documents? | Refuse: requested information is absent from the corpus. | None |
| q06 | Is the AI RMF intended only for one industry or use case, and is its use mandatory? | It is intended to be voluntary, rights-preserving, non-sector-specific, and use-case agnostic, with flexibility for organizations of different sizes and sectors. | [RMF 7](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=7) |
| q07 | What two components form the AI RMF definition of risk? | The probability of an event occurring and the magnitude or degree of its consequences. | [RMF 9](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=9) |
| q08 | Does the AI RMF prescribe a universal risk tolerance, and what influences acceptable risk? | It does not prescribe risk tolerance. Acceptable risk depends on context, application, objectives, legal requirements, policies, norms, organizational priorities, and resources. | [RMF 12](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=12) |
| q09 | Why can third-party components make AI risk measurement harder? | Developer and deployer metrics may differ, developer methods may be opaque, and integration choices can introduce risks without adequate governance and safeguards. | [RMF 10](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=10) |
| q10 | What should happen when an AI system presents unacceptable negative risk levels? | Development and deployment should cease safely until the risks can be sufficiently managed. | [RMF 13](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=13) |
| q11 | How does the AI RMF define reliability in terms of performance, time, and conditions? | Performing as required without failure for a given time interval under given conditions, with correctness during expected use over time. | [RMF 18](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=18) |
| q12 | How does the AI RMF distinguish transparency, explainability, and interpretability? | Transparency concerns what happened, explainability how a decision was made, and interpretability why it was made and its meaning or context for the user. | [RMF 22](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=22) |
| q13 | Which three major categories of AI bias does NIST identify in the AI RMF? | Systemic bias, computational and statistical bias, and human-cognitive bias. | [RMF 23](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=23) |
| q14 | What are the four AI RMF Core functions, and which function cuts across the others? | GOVERN, MAP, MEASURE, and MANAGE. Governance is a cross-cutting function that informs and is infused throughout the other three. | [RMF 25](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=25) |
| q15 | How should organizations connect AI risk management to enterprise risk management? | Integrate AI risk management into broader enterprise risk strategies and processes, alongside risks such as cybersecurity and privacy, rather than treating AI risks in isolation. | [RMF 13](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=13) |
| q16 | Which AI RMF function establishes the context for risk, and which uses quantitative, qualitative, or mixed methods to assess it? | MAP establishes context for AI risk. MEASURE uses quantitative, qualitative, or mixed-method tools to assess, benchmark, and monitor risk and its impacts. | [RMF 29](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=29), [RMF 33](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=33) |
| q17 | Which four primary considerations limited the scope of the GAI Public Working Group described in the introduction? | Governance, Content Provenance, Pre-deployment Testing, and Incident Disclosure. | [GenAI 6](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=6) |
| q18 | Which privacy principles can be put at risk when personal data is used to train generative AI? | Transparency, individual participation including consent, and purpose specification. | [GenAI 11](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=11) |
| q19 | What is automation bias, and how can it worsen generative AI risks? | It is excessive deference to automated systems. Over-reliance can lead people to overvalue generated content and exacerbate confabulation, bias, and homogenization risks. | [GenAI 13](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=13) |
| q20 | What can over-reliance on synthetic training data do to a generative model? | It can cause model collapse: data points disappear from the output distribution, threatening robustness and increasing homogenized outputs. | [GenAI 13](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=13) |
| q21 | How do direct and indirect prompt injection differ in the GenAI Profile? | Direct attacks submit malicious prompts to the GAI system. Indirect attacks place prompts in data likely to be retrieved by an LLM-integrated application. | [GenAI 15](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=15) |
| q22 | During which two phases does action MS-2.5-003 recommend checking sources and citations in GAI outputs? | During pre-deployment risk measurement and ongoing monitoring activities. | [GenAI 35](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=35) |
| q23 | What kinds of information can content provenance metadata record for generative AI? | Model developers or content creators, creation date and time, location, modifications, and sources. | [GenAI 55](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=55) |
| q24 | What background should an effective AI red team bring to a deployment context? | Domain expertise and awareness of the socio-cultural context; demographic and interdisciplinary diversity can help identify flaws across different contexts. | [GenAI 54](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=54) |
| q25 | Why may human-exam scores and laboratory benchmarks fail to establish generative AI reliability in actual use? | Anecdotal human-test results do not guarantee validity or reliability, and laboratory benchmarks can be mismatched to diverse real-world deployment contexts. | [GenAI 53](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=53) |
| q26 | Compare the AI RMF general privacy aims with the GenAI Profile concerns about personal training data. | The AI RMF emphasizes autonomy, identity, dignity, and control over disclosure. The GenAI Profile highlights training-data risks to transparency, participation and consent, and purpose specification. | [RMF 22](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=22), [GenAI 11](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=11) |
| q27 | What Recall@5 score did Gemini 3.8 Flash achieve on these two NIST PDFs? | Refuse: requested information is absent from the corpus. | None |
| q28 | What exact cosine-similarity threshold does NIST mandate for accepting a RAG answer as supported? | Refuse: requested information is absent from the corpus. | None |
| q29 | What exact Python function implementation for Reciprocal Rank Fusion retrieval is provided in these PDFs? | Refuse: requested information is absent from the corpus. | None |
| q30 | What uniform annual dollar budget does NIST require every organization to spend implementing the AI RMF? | Refuse: requested information is absent from the corpus. | None |

## Source verification

Every page number is a one-based physical PDF page, including covers and contents. Original PDF
SHA-256 identities match [the corpus reference](../docs/corpus-reference.md). Source pages were
extracted using the production pipeline; each anchor group below fits within one default
400-word chunk with 80-word overlap on its labeled page. This verifies text availability, not
retrieval ranking or generated-answer correctness.

Anchors are evidence-review notes, not extra fields in the strict golden schema. Read the
surrounding source paragraphs through the page links above.
- q01, RMF 19: “and details about test methodology”.
- q02, RMF 20: “starting as early as possible with planning and design”.
- q03, GenAI 10: “diverge from the prompts or other input”; “contradict previously generated statements in the same context”.
- q04, GenAI 12: “model distillation or compression”.
- q06, RMF 7: “voluntary, rights-preserving, non-sector-specific, and use-case agnostic”.
- q07, RMF 9: “probability of occurring and the magnitude or degree”.
- q08, RMF 12: “it does not prescribe risk tolerance”; “highly contextual and application and use-case specific”.
- q09, RMF 10: “may not align with the risk metrics”; “may not be transparent”.
- q10, RMF 13: “development and deployment should cease in a safe manner”.
- q11, RMF 18: “without failure, for a given time interval, under given conditions”.
- q12, RMF 22: “Transparency can answer the question”; “meaning or context to the user”.
- q13, RMF 23: “systemic, computational and statistical, and human-cognitive”.
- q14, RMF 25: “GOVERN , MAP, MEASURE , and MANAGE”; “cross-cutting function”.
- q15, RMF 13: “AI risks should not be considered in isolation”; “broader enterprise risk management strategies and processes”.
- q16, RMF 29: “establishes the context to frame risks”.
- q16, RMF 33: “quantitative, qualitative, or mixed-method tools”.
- q17, GenAI 6: “Governance, Content Provenance, Pre-deployment Testing, and Incident Disclosure”.
- q18, GenAI 11: “individual participation (including consent)”.
- q19, GenAI 13: “excessive deference to automated systems”; “Automation bias can exacerbate other risks”.
- q20, GenAI 13: “model training over-relies on synthetic data”; “data points disappearing”.
- q21, GenAI 15: “input them directly to a GAI system”; “injecting prompts into data likely to be retrieved”.
- q22, GenAI 35: “Review and verify sources and citations”; “ongoing monitoring activities”.
- q23, GenAI 55: “Provenance metadata can include information”; “date/time of creation”.
- q24, GenAI 54: “domain expertise”; “awareness of socio-cultural aspects”.
- q25, GenAI 53: “does not guarantee GAI system validity or reliability”; “mismatches between laboratory and real-world settings”.
- q26, RMF 22: “human autonomy”; “identity, and dignity”.
- q26, GenAI 11: “individual participation (including consent)”.

## Unanswerable labels

- q05: Both publications predate 2025 and all 112 extracted pages lack the year 2025; they cannot report the requested confirmed annual total.
- q27: Neither PDF mentions Gemini 3.8 or reports this model/corpus benchmark. Application measurements are not evidence inside these PDFs.
- q28: Neither PDF contains cosine-similarity requirements or a mandated numerical RAG acceptance threshold; no such threshold can be cited.
- q29: Neither PDF contains Reciprocal Rank Fusion or the requested Python implementation. Producing generic code would not answer from the corpus.
- q30: The PDFs do not prescribe the requested uniform annual dollar budget. The AI RMF is voluntary and context-specific; resource discussion supplies no mandatory amount.

## Provenance and interpretation

Golden SHA-256: `b1307136fd933bf5b2cf36a1208304e1dfc06dc69f8c939a4a73b95e78224c56`. Source files
were checked on 2026-10-26. Schema validation reports 30 / 25 / 5; source/hash/page/chunk checks
passed. No model-quality score follows from these checks. Actual runs must retain their code
revision, dataset digest, settings, and error counts.

Canonical pages are not an exhaustive list of interchangeable sources. Review apparent page
misses before concluding there is no valid evidence. The current recall metric treats multiple
gold pages as jointly expected; do not add alternative duplicate pages as if all were required.

Five negative questions give refusal accuracy only in 20-percentage-point increments. The
negatives request missing statistics, model results, prescribed thresholds/budgets, and code;
broader real-user, adversarial, and conversational coverage remains unmeasured. Some questions
share topics or pages, so they are not independent samples.

Keep labels fixed during strategy comparisons. Correct labels only when source evidence warrants
it, document the change, and rerun all strategies on the same digest. This set has been read
during development and is not an independent held-out test set. Add separately
authored/independently reviewed questions before stronger generalization claims.

Use the [browser evaluation handoff](README.md#run-from-github-actions) for an explicit real run.
The repository secret stays in Actions. Reference answers are not passed to the answering model,
and no fake-provider result is a semantic benchmark.
