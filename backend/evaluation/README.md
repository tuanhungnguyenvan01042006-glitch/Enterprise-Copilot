# Retrieval evaluation setup

This directory is separate from the application runtime. `baseline.json` records
the document checksums and revision, Qdrant counts and a fingerprint covering
each point's ID, payload and vector. It records the current code configuration;
it cannot prove which model produced an existing point because the collection
does not store model/version provenance. This fingerprint detects a changed
collection but is not a backup or an immutable snapshot.

Capture the baseline from the Compose database and Qdrant (the command writes
the current `baseline.json`; retain any previous copy you want to compare):

```powershell
docker compose up -d db qdrant
docker compose run -T --rm --no-deps -e PYTHONPATH=/app -v "${PWD}\backend\evaluation:/evaluation" api python /evaluation/capture_baseline.py
```

For the isolated evaluation environment on Windows, from the project root:

```powershell
py -3.12 -m venv backend/evaluation/.venv
$env:PYTHONUTF8='1'
backend/evaluation/.venv/Scripts/python.exe -m pip install -r backend/evaluation/requirements.txt
$env:PYTHONPATH=(Resolve-Path backend).Path
backend/evaluation/.venv/Scripts/python.exe backend/evaluation/smoke_test.py
```

The smoke test uses fake models and fake contexts and calls no external model.
It checks the Ragas generator adapter, application retrieval import, and an
ID-based recall calculation. It does not generate a real testset or verify an
LLM provider. Ragas testset generation and LLM-judged metrics need a separately
configured LLM provider and credentials; Voyage's embedding key is not an LLM
key. The selected LLM provider is OpenAI; set `OPENAI_API_KEY` in the project
root `.env` or process environment. `OPENAI_EVAL_MODEL` defaults to
`gpt-4o-mini` and can be overridden in the same way. The default is for the
initial pilot; review the model's availability and quality for the benchmark.
Ragas testset generation uses Voyage document embeddings and `VOYAGE_API_KEY`.

With those settings, check OpenAI using a small synthetic prompt:

```powershell
$env:PYTHONPATH=(Resolve-Path backend).Path
backend/evaluation/.venv/Scripts/python.exe backend/evaluation/check_openai.py
```

This request is billable according to the OpenAI account's pricing and usage.
The check sends no project documents. Do not commit API keys or put them in
`.env.example`.

The two known empty-after-cleaning chunks are recorded in the baseline. Neither
the snapshot nor this smoke test evaluates retrieval quality. Access control and
metadata synchronization remain necessary before retrieval is exposed to users.

## Small Ragas pilot

`generate_pilot.py` reads three specific chunks from Qdrant and generates six
single-hop examples through OpenAI and Voyage. It creates `pilot/sources.json`,
`pilot/testset_raw.json`, and `pilot/usage.json`; it refuses to overwrite an
existing testset. These artifacts contain document text and should be handled
accordingly. The usage figures capture successful calls observed by the local
callbacks, not the provider's final invoice. Prior failed attempts are saved in
separate `pilot/usage-attempt*.json` files.

`pilot/testset_review.json` records an initial review against the selected
source chunks. It has not been approved by a domain expert; do not use it as
ground truth until it has been reviewed and corrected. The generation command
sends the selected chunks to the configured model providers and incurs usage.

## Refined pilot (12 November 2026)

`generate_pilot_v2.py` uses the same OpenAI model, a fixed employee persona,
grammatical medium-length questions, a condition-preserving prompt, and Ragas
keyphrase extraction. The final selection is 15 separate chunks from five
documents, yielding one case per chunk. Single-hop generation does not need
similarity embeddings, so these runs make no Voyage embedding requests.

The first attempt (`pilot_v2/`) used five chunks and produced many duplicate
information needs. It is preserved as an experiment. The refined run is in
`pilot_v2_refined/`: `testset_raw.json` is untouched model output;
`testset_accepted_raw.json` contains the ten raw cases accepted by the assistant;
`testset_curated.json` contains all 15 after explicit source-grounded edits to
five cases. Before-edit fields and the edit flag distinguish edited references
from raw output. No cases have domain-expert approval yet.

`review_annotations.json` is an assistant's case-specific review, not an automatic
grader. `build_pilot_review.py` validates raw-file hashes, attaches exact source
IDs, and builds `pilot_comparison.json` and per-run reviewed files. It refuses
to apply old annotations if raw files change. Reproducing the review makes no
API calls:

```powershell
backend/evaluation/.venv/Scripts/python.exe backend/evaluation/build_pilot_review.py
```

Generating a new independent run is billable and requires a fresh output path:

```powershell
$env:PYTHONPATH=(Resolve-Path backend).Path
backend/evaluation/.venv/Scripts/python.exe backend/evaluation/generate_pilot_v2.py --output-dir backend/evaluation/pilot_next
```

Overall acceptance on the common rubric is 2/6 for the original pilot and 10/15
for the refined raw pilot. The original case 02 was too harshly labeled in the
first review; its answer preserves the conditional guidance, so it is accepted
on re-review. The historic raw data and review are retained. On the same three
original chunks, the refined run has only 1/3 accepted versus the original 2/6;
there is not evidence here that prompts alone fixed difficult policy conditions.
These are small assistant-reviewed synthetic sets, not retrieval benchmark scores.

## Final 50-question set (16 November 2026)

`final_plan.json` selects 55 distinct indexed chunks from 11 documents for exactly
35 single-hop and 15 two-context multi-hop cases. Topics cover expenses, acceptable
use/security, onboarding, development, time off, wellness benefits, mentorship,
responsibility and confidentiality. Multi-hop includes comparisons and connected
policy applications, including cross-document cases. This is a deliberately
stratified synthetic benchmark, not an estimate of production query frequency or
coverage of all 163 documents.

`generate_final.py` reuses the pilot-v2 instruction, employee persona, keyphrase
focus and grammatical English, adding typed evidence quotes, separate few-shot
examples for comparisons/bridges, and a separate automated review call. For this
small fixed plan it uses the existing LangChain/OpenAI structured-output API
directly instead of Ragas random scenario sampling or a new similarity graph.
Keyphrases are extracted in the question-generation call, not through the Ragas
KeyphrasesExtractor transform. No new dependencies or embedding calls are needed.

Run from the project root (billable; selected source text is sent to OpenAI):

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH=(Resolve-Path backend).Path
$env:OPENAI_EVAL_MODEL='gpt-4.1-mini'
backend/evaluation/.venv/Scripts/python.exe backend/evaluation/generate_final.py
backend/evaluation/.venv/Scripts/python.exe backend/evaluation/finalize_testset.py
```

The source snapshot is read from Qdrant once; the index is never modified. Each
case gets at most eight generation attempts. Failed validation or reviews feed back
into the next generation attempt. Per-case JSON files preserve all returned
candidates, reviews and feedback and permit resuming an interrupted run. Network
failures fail the run while preserving completed checkpoints. Resuming requires
the same plan, prompts and model; changes require a fresh `--output-dir`.
An existing generated or final file is never overwritten. `usage.json` accumulates usage for
each invocation, including failed runs observed by the callbacks.

The final run uses `gpt-4.1-mini`. Earlier interrupted `gpt-4o-mini` experiments
are retained in `final_attempt1/` and `final_v1/`; neither is a final benchmark.
Callback usage from an abruptly interrupted process may be missing; the final
run's usage must not be presented as total spend across all experiments.

Artifacts in `final_v2/`:

- `testset_final.json`: the 50 selected cases, with Ragas-compatible question,
  reference, contexts and context-ID fields plus provenance and review metadata.
- `testset_generated.json`, when generation passes for all 50 cases: automatically
  accepted candidates before assistant curation. In this run one case failed
  schema validation, so no complete pre-curation file was emitted; inspect the
  individual case files for the 49 accepted raw cases.
- `sources.json`: the exact 55 source texts and original indexed metadata.
- `cases/`: structured candidate outputs and automated review history. New attempts
  retain `candidate_raw` before evidence anchoring. If an excerpt is not verbatim,
  `anchor_evidence` expands it to the full exact source chunk instead of guessing
  or accepting an altered quote. The answer and evidence contribution still have
  to pass the reviewer; expansion is recorded explicitly.
- `run_config.json`: source plan, complete prompts and model name.
- `usage.json`: callback-observed usage estimates and source snapshot hashes.
- `assistant_edits.json` and `curation_reviews.json`: 18 explicit source-grounded
  edits and their model reviews, also planned in `final_edits.json`.
- `curation_usage.json`: callback usage for the explicit-edit review step.

`finalize_testset.py` applies the explicit edits in `final_edits.json`, checks
them with the same configured model, and validates all 50 cases before writing
the final file. It preserves before-edit values and edit reasons. Seventeen
edits refine automatically accepted cases; one supplies a source-grounded case
after repeated schema failures. Thus this is a curated final set, not 50/50
untouched successful model generations. Review caches are reused only for the
same candidate. If generation exits because a case fails, its retained checkpoints
can still be finalized when an explicit source-grounded edit covers that case.
For a new run, pass the same fresh `--output-dir` to both commands.

The reviewer checks answer faithfulness, qualifiers, meaningful context connection
and whether each context is necessary. Local validation checks verbatim quotes,
source counts/IDs, the exact distribution and question similarity. The reviewer
uses the same model as generation: this is not independent expert validation.
`human_approved` remains false. The source-removal check is model judged against
the selected pair; alternative answer-bearing chunks elsewhere in the corpus
have not been exhaustively excluded. Do not equate two contexts with two dependent
reasoning steps: inspect `reasoning_type` to distinguish comparison from bridge.

Offline checks (no model calls):

```powershell
backend/evaluation/.venv/Scripts/python.exe -m pytest backend/evaluation/test_generate_final.py backend/evaluation/test_pilot_v2.py backend/evaluation/test_openai_config.py -q
```

Use `question_type` for separate single-hop/multi-hop retrieval reports and
`reference_context_ids` as the required evidence set. For multi-hop, report both
partial evidence recall and the fraction of questions whose complete required
evidence set is retrieved. This generation step does not run the retrieval
benchmark or establish that a RAG system passes it.
