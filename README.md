# MAESTRO-bench

**MAESTRO Experiment Bench** – a small, self-hosted platform to run and trace
experiments with pipelines of LLM agents over tabular datasets.

You describe *agents* (a prompt + a model), assemble them into an ordered
pipeline, point the pipeline at a CSV/JSON dataset, and MAESTRO-bench runs every
row through the pipeline while recording an immutable snapshot of the exact
prompts, models, parameters and outputs used. The typical use case is
evaluating LLM-based graders or tutors on learner answers, but nothing in the
engine is specific to education.

![MAESTRO-bench](frontend/public/MAESTRO-bench.png)

## Features

- **Prompts with versions** – reusable prompts, each with versioned system/user
  templates and declared variables (`{{ variable }}` or `<variable></variable>`).
- **Models** – any provider supported by [LiteLLM](https://docs.litellm.ai/docs/providers)
  (OpenAI, Anthropic, Mistral, Groq, Together, DeepSeek out of the box).
- **Agents and teams** – an agent is a prompt version + a default model, grouped
  into teams.
- **Experiments** – a visual flow editor to chain agents, map dataset columns and
  previous agent outputs to prompt variables, and pick a sampling strategy
  (all rows, random sample, row range).
- **Batches** – run one setup with several models, prompt versions or
  temperatures at once. From an experiment, "Vary…" copies its configuration;
  you pick the values to try per agent, and one experiment starts per
  combination. The batch page follows them together and opens the analysis
  editor pre-filled with its executions.
- **Executions and traces** – every run stores a snapshot of the configuration
  actually used, per-agent messages/outputs, token counts, cost and latency,
  and produces a downloadable JSON results file.
- **Analyses** – compare one or more executions to a ground-truth dataset column:
  RMSE, MAE, bias, Pearson and Spearman correlations for numeric outputs;
  accuracy, macro F1, Cohen's κ and quadratic weighted κ for labels. Every
  metric comes with a bootstrap confidence interval and the share of rows that
  could be used.

## Architecture

```
maestro-bench/
├── backend/     FastAPI + SQLModel (SQLite) + LiteLLM
├── frontend/    Nuxt 4 + Nuxt UI single-page app
└── datasets/    CSV/JSON files referenced by dataset records
```

- Backend: `backend/main.py` exposes the REST API (OpenAPI docs at `/docs`).
  Experiments run as asyncio tasks inside the API process
  (`backend/async_jobs.py`), through the pipeline engine in `backend/core/`.
- Frontend: talks to the backend over HTTP; the base URL comes from
  `NUXT_PUBLIC_BACK_URL`.
- Storage: a SQLite file (`backend/app.db` by default) plus JSON result files in
  `backend/results/`.

## Quick start

### Prerequisites

- At least one LLM provider API key (OpenAI, Anthropic or Mistral).
- Either **Docker + Docker Compose**, or for local development
  [uv](https://docs.astral.sh/uv/) (Python 3.12+) and
  [pnpm](https://pnpm.io/) (Node.js 22+).

### 1. Configure

```bash
cp backend/.env.example backend/.env    # add your API key(s)
cp frontend/.env.example frontend/.env  # only needed outside Docker
```

### 2a. Run with Docker Compose

```bash
docker compose up --build
```

### 2b. Run locally

Backend:

```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

Frontend (in another terminal):

```bash
cd frontend
pnpm install
pnpm dev
```

### 3. Seed sample data (optional)

The database starts empty. The seed script creates a few Mistral models, three
example prompts (two graders and a "meta-tutor"), two agent teams and the
sample datasets shipped in `datasets/`.

```bash
cd backend
uv run python scripts/seed.py
# with Docker: docker compose exec backend uv run python scripts/seed.py
```

> **Warning:** the seed script deletes all existing models, prompts, agents,
> teams and datasets before inserting the samples.

Then open <http://localhost:3000>. The API is at <http://localhost:8000>
(interactive docs at <http://localhost:8000/docs>).

## Usage

1. **Models** – register the models you want to use (name as expected by the
   provider, e.g. `gpt-4o-mini`, `claude-sonnet-4-20250514`,
   `mistral-medium-2505`). The dashboard shows which providers have an API key
   configured.
2. **Prompts** – create a prompt and at least one version. Declare the variables
   the templates use so they can be mapped later.
3. **Agents** – create a team, then agents with a default prompt version and
   model.
4. **Datasets** – copy your CSV or JSON file into the top-level `datasets/`
   directory, then create a dataset record pointing to it (path relative to
   `datasets/`, e.g. `my_data.csv`). There is no file upload in the UI.
5. **Experiments** – pick a dataset, drag agents onto the canvas, connect them
   to define the execution order, map each prompt variable to a dataset column,
   a previous agent's output or a static value, choose a sampling strategy and
   launch. The experiment starts immediately; reload the page to see its status
   change.
6. **Batches** – to try other models, prompt versions or temperatures on a
   setup that works, open its experiment and click **Vary…**. The form is
   pre-filled; add a variation (an agent, the field to change and the values to
   try). One experiment is created per combination, all started at once and
   grouped in a batch: the experiment you started from is not rerun. A prompt
   version can only be tried if the agent's input mappings cover its variables.
   With a random sample, all the experiments of a batch run on the same rows. Past 10 experiments you are asked to confirm, and 50 is the maximum. Deleting
   a batch keeps its experiments. Providers' rate limits apply across the whole
   batch (see `<PROVIDER>_MAX_RPS` below), so runs on the same provider share
   its quota.
7. **Results** – open an experiment to inspect its executions and per-agent
   traces, or download the full JSON results file.
8. **Analyses** – click **Analyze** on an experiment (or create one from the
   Analyses page), pick the dataset column holding the ground truth and the
   path to the prediction in the agent's JSON output (e.g. `score`), choose
   numeric or categorical metrics, and add other executions to compare.
   Analyses are saved as configurations and recomputed from the results files
   each time they are opened. Rows that cannot be used (agent error, output not
   JSON, path missing, invalid value, missing ground truth) are excluded and
   reported, never counted as 0.

   The same computation is available without saving through
   `POST /analyses/compute`, for scripts and notebooks:

   ```python
   import httpx

   result = httpx.post("http://localhost:8000/analyses/compute", json={
       "config": {
           "truth_column": "score_avg",
           "output_path": "score",
           "value_type": "numeric",
           "metrics": ["rmse", "mae", "pearson", "spearman", "bias"],
       },
       "runs": [{"execution_id": 1, "agent_name": "Corrector"}],
   }).json()
   ```

   New metrics are plain functions registered in `backend/analysis/metrics.py`.

## Tests

```bash
cd backend
uv run pytest
```

## Configuration

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY` | – | Provider API keys (at least one). `GROQ_API_KEY`, `TOGETHER_API_KEY`, `DEEPSEEK_API_KEY` are also recognised. |
| `LLM_MAX_RETRIES` | `6` | Retries on transient provider errors (429, timeouts, 5xx), with exponential backoff that honours `Retry-After`. `LLM_RETRY_BASE_DELAY` / `LLM_RETRY_MAX_DELAY` (`1` / `60` s) tune the backoff. |
| `<PROVIDER>_MAX_RPS` | – | Optional requests-per-second cap per provider, e.g. `MISTRAL_MAX_RPS=1`. Shared by all running experiments. |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | Bind address when running `python main.py`. |
| `DATABASE_URL` | `sqlite:///./app.db` | SQLAlchemy connection string. |
| `DB_ECHO` | `false` | Log SQL statements. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins. |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|---|---|---|
| `NUXT_PUBLIC_BACK_URL` | `http://localhost:8000` | Backend URL as seen from the browser. |

## Sample datasets

- `datasets/mohler_dataset.csv` – the short-answer grading dataset from
  Mohler, Bunescu and Mihalcea, *Learning to Grade Short Answer Questions using
  Semantic Similarity Measures and Dependency Graph Alignments* (ACL 2011).
- `datasets/diff_gt_2_mohler_dataset.csv` – the subset of the above where the
  two human graders disagree by more than 2 points.
- `datasets/french_answers.csv` – a tiny synthetic French sample for smoke tests.

## Development notes

- Backend lint: `uvx ruff check backend`.
- Frontend lint: `pnpm lint` in `frontend/` (ESLint with `@antfu/eslint-config`).
- Results files are written to `backend/results/` and referenced from the
  `experimentexecution` table; both are git-ignored.
- The database schema is created automatically on startup with
  `SQLModel.metadata.create_all`; there is no migration tool, so delete
  `backend/app.db` after changing `backend/tables.py`.
