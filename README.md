<img src="frontend/public/icon-512.png" alt="MAESTRO-bench logo" width="72">

# MAESTRO-bench

**MAESTRO-Bench** - a small, self-hosted platform to run and trace
experiments with pipelines of LLM agents over tabular datasets.

You describe *agents* (a prompt + a model), assemble them into an ordered
pipeline, point the pipeline at a CSV/JSON dataset, and MAESTRO-bench runs every
row through the pipeline while recording an immutable snapshot of the exact
prompts, models, parameters and outputs used.

## Features

- **Prompts with versions** - reusable prompts, each with versioned system/user
  templates and declared variables (`{{ variable }}` or `<variable></variable>`).
- **Models** - any provider supported by [LiteLLM](https://docs.litellm.ai/docs/providers)
  (OpenAI, Anthropic, Mistral, Groq, Together, DeepSeek out of the box).
- **Agents** - an agent is a prompt version + a default model, or an aggregator
  that combines other agents' outputs. Tag them to group them.
- **Experiments** - a visual flow editor to chain agents, map dataset columns and
  previous agent outputs to prompt variables, and pick a sampling strategy
  (all rows, random sample, row range).
- **Batches** - run one setup with several models, prompt versions or
  temperatures at once, and follow the resulting experiments together.
- **Executions and traces** - every run stores a snapshot of the configuration
  actually used, per-agent messages/outputs, token counts, cost and latency,
  and produces a downloadable JSON results file.
- **Analyses** - compare one or more executions to a ground-truth dataset column:
  RMSE, MAE, bias, Pearson and Spearman correlations for numeric outputs;
  accuracy, macro F1, Cohen's κ and quadratic weighted κ for labels. Every
  metric comes with a bootstrap confidence interval and the share of rows that
  could be used.
- **Public links** - share an experiment, a batch, an analysis or a study with
  peers through a read-only link that needs no account (see
  [Public links](#public-links)).

## Architecture

```
maestro-bench/
├── backend/     FastAPI + SQLModel (PostgreSQL) + Alembic + LiteLLM
└── frontend/    Nuxt 4 + Nuxt UI single-page app
```

- Backend: `backend/main.py` exposes the REST API (OpenAPI docs at `/docs`).
  Experiments run as asyncio tasks inside the API process
  (`backend/async_jobs.py`), through the pipeline engine in `backend/core/`.
- Frontend: talks to the backend over HTTP; the base URL comes from
  `NUXT_PUBLIC_BACK_URL`.
- Storage: a PostgreSQL database (schema managed by Alembic migrations, applied
  automatically on startup) plus files on disk under `DATA_DIR`. Each workspace
  has its own folder, `<DATA_DIR>/workspaces/<id>/`, with its datasets in
  `datasets/` and its JSON result files in `results/`. Under Docker Compose they
  live in the `maestro-data` volume.

## Quick start

### Prerequisites

- At least one LLM provider API key (OpenAI, Anthropic or Mistral), or a local
  [Ollama](https://ollama.com) server (no key needed).
- Either **Docker + Docker Compose**, or for local development
  [uv](https://docs.astral.sh/uv/) (Python 3.12+),
  [pnpm](https://pnpm.io/) (Node.js 22+) and a PostgreSQL server (the Compose
  `postgres` service works for that).

### 1. Configure

```bash
cp backend/.env.example backend/.env    # add your API key(s)
cp frontend/.env.example frontend/.env  # only needed outside Docker
```

Every page and every API route needs a signed-in user. Sign-in goes through
GitLab (OpenID Connect), so before the first start:

1. In GitLab, create an application (**Edit profile → Applications**, or a
   group's **Settings → Applications**) with the redirect URI
   `http://localhost:8000/auth/gitlab/callback`, **Confidential** ticked and the
   scopes `openid`, `profile` and `email`.
2. Put its ID and secret in `backend/.env` (`AUTH_GITLAB_*`), along with a
   `SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
   and who may sign in (`AUTH_ALLOWED_EMAIL_DOMAINS` and/or
   `AUTH_GITLAB_ALLOWED_GROUPS`).

The backend refuses to start without a secret, a provider and an allowlist.
See [Configuration](#configuration) for every setting.

### 2a. Run with Docker Compose

```bash
mkdir -p backend/results   # so the folder is created by you, not by Docker
docker compose up --build
```

This starts PostgreSQL, the backend (which applies the database migrations on
startup) and the frontend. The database lives in the `maestro-pgdata` Docker
volume. Set `POSTGRES_PASSWORD` in your shell or a root `.env` to change the
default password (`maestro`).

### 2b. Run locally

Start only the database with Docker (it listens on `127.0.0.1:5432`, which is
what the default `DATABASE_URL` expects):

```bash
docker compose up -d postgres
```

Backend:

```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

Outside Docker, `DATA_DIR` defaults to the repository root: files go under
`workspaces/<id>/` there.

Frontend (in another terminal):

```bash
cd frontend
pnpm install
pnpm dev
```

### 3. Seed sample data (optional)

The database starts empty. The seed script creates a few Mistral models, three
example prompts (two graders and a "meta-tutor"), three agents and the
sample datasets shipped in `backend/scripts/sample_datasets/`, copied into the
workspace's `datasets/` folder.

```bash
cd backend
uv run python scripts/seed.py
# with Docker: docker compose exec backend uv run python scripts/seed.py
```

The script only adds what is missing (matched by name or file) and never
deletes or modifies anything, so it is safe to run on a database that already
holds your data, and to run again. It fills one workspace, `default` unless you
pass `--workspace <slug>`.

Then open <http://localhost:3000>. The API is at <http://localhost:8000>
(interactive docs at <http://localhost:8000/docs>).

## Usage

A new workspace shows a **Get started** list at the bottom of the sidebar: connect a
provider, add a dataset, write a prompt, register a model, create an agent, run an
experiment. It ticks itself from what the workspace holds (`GET /setup`), and
goes away once everything is done or when hidden. `C` creates what the current
page lists (a dataset on Datasets, a prompt on Prompts...), an experiment elsewhere.

1. **Models** - register the models you want to use (name as expected by the
   provider, e.g. `gpt-4o-mini`, `claude-sonnet-4-20250514`,
   `mistral-medium-2505`; for Ollama, the tag you pulled, e.g. `llama3.2:3b`,
   under the `ollama` provider). **Settings** shows which providers have an API
   key or server URL configured.
2. **Prompts** - create a prompt and at least one version. Declare the variables
   the templates use so they can be mapped later.
3. **Agents** - agents with a default prompt version and model. Tag them to
   find them again.
4. **Datasets** - upload a CSV (UTF-8) or JSON file (a list of objects) with
   **New dataset**; it needs a header row and at least one row, and is limited
   to `MAX_UPLOAD_MB`. The file is stored in the workspace's own folder under a
   name the server picks. Open a dataset to browse, search and edit its rows in a keyboard-driven grid (`?`
   lists the shortcuts; `⌘S` saves). Edits rewrite the file on disk, and a
   file changed elsewhere since it was opened is never overwritten. Up to
   100,000 rows.
5. **Experiments** - pick a dataset, drag agents onto the canvas, connect them
   to define the execution order, map each prompt variable to a dataset column,
   a previous agent's output or a static value, choose a sampling strategy and
   launch. The experiment starts immediately, or waits in a queue (status
   *queued*, cancellable) when your workspace already runs as many as it may;
   see the limits under Configuration. Reload the page to see its status change.
6. **Batches** - on an experiment, click **Vary…**, pick the values to try
   (model, prompt version or temperature) per agent, and one experiment starts
   per combination (max 50, confirmation past 10). They share the same rows
   when sampling randomly, and share provider rate limits
   (`<PROVIDER>_MAX_RPS`). Deleting a batch keeps its experiments.
7. **Results** - open an experiment to inspect its executions and per-agent
   traces, or download the full JSON results file.
8. **Analyses** - click **Analyze** on an experiment (or create one from the
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

## Tests and CI

```bash
# Backend (with the Compose stack running, so PostgreSQL is available)
docker compose exec backend uv run pytest

# Frontend
cd frontend
pnpm lint && pnpm typecheck && pnpm test
```

GitLab CI (`.gitlab-ci.yml`) runs the same checks on every merge request and on the
default branch, in two parallel jobs:

- `backend`: ruff, then `alembic upgrade head` on an empty database followed by
  `alembic check` (so a model change without its migration fails), then pytest.
- `frontend`: ESLint, the Nuxt type check and vitest.

Both publish a JUnit report, shown in the merge request. The ruff version is pinned
in `.gitlab-ci.yml` (`RUFF_VERSION`).

## Configuration

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY` | - | Provider API keys (at least one). `GROQ_API_KEY`, `TOGETHER_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY` (provider `google`), `XAI_API_KEY`, `CEREBRAS_API_KEY`, `PERPLEXITYAI_API_KEY` and `OPENROUTER_API_KEY` are also recognised. For any other [LiteLLM provider](https://docs.litellm.ai/docs/providers), add it to `SUPPORTED_PROVIDERS` in `backend/core/llm.py`. |
| `OLLAMA_API_BASE` | - | URL of an [Ollama](https://ollama.com) server, e.g. `http://localhost:11434`. Setting it enables the `ollama` provider (no key). Under Docker use `http://host.docker.internal:11434`. Cost is reported as 0. |
| `LLM_MAX_RETRIES` | `6` | Retries on transient provider errors (429, timeouts, 5xx), with exponential backoff that honours `Retry-After`. `LLM_RETRY_BASE_DELAY` / `LLM_RETRY_MAX_DELAY` (`1` / `60` s) tune the backoff. |
| `<PROVIDER>_MAX_RPS` | - | Optional requests-per-second cap per provider, e.g. `MISTRAL_MAX_RPS=1`. Shared by all running experiments. |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | Bind address when running `python main.py`. |
| `DATABASE_URL` | `postgresql+psycopg://maestro:maestro@localhost:5432/maestro` | SQLAlchemy connection string. PostgreSQL only. Docker Compose sets it to the `postgres` service. |
| `DATA_DIR` | repository root (`/data` in Docker) | Where files are stored: `<DATA_DIR>/workspaces/<id>/datasets/` and `.../results/`, one folder per workspace. Paths saved in the database are relative to those two folders, and a path that leaves its folder is refused. |
| `MAX_UPLOAD_MB` | `50` | Largest dataset file accepted by an upload. |
| `MAX_CONCURRENT_EXPERIMENTS_PER_WORKSPACE` | `3` | Experiments one workspace runs at once. The next ones wait, in order, and start as soon as a slot is free. |
| `MAX_CONCURRENT_EXPERIMENTS` | `8` | Experiments the whole instance runs at once, all workspaces together. A workspace that is at its own limit never holds back another. |
| `POSTGRES_PASSWORD` | `maestro` | Read by `docker-compose.yml` only: password of the `postgres` service and of the backend's connection. |
| `DB_ECHO` | `false` | Log SQL statements. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins. |
| `SECRET_KEY` | - (required) | At least 32 characters. Signs the OAuth state and derives the CSRF tokens. Changing it only interrupts the sign-ins in progress. |
| `ENCRYPTION_KEY` | - | At least 32 random characters (`python -c "import secrets; print(secrets.token_urlsafe(48))"`). Encrypts the API keys that workspaces store. Without it workspaces cannot store keys and only the instance's keys are used. **Changing it makes the stored keys unreadable**: owners must set them again. Keep it apart from `SECRET_KEY`. |
| `PROVIDERS_INSTANCE_FALLBACK` | `true` | Whether a workspace without its own key for a provider uses the instance's key. Set to `false` to make every workspace bring its own keys: its runs then fail with a clear message until an owner sets one. Providers set by URL (Ollama) are instance-wide and unaffected. |
| `PUBLIC_SHARING_ENABLED` | `true` | Whether editors can make public read-only links (see [Public links](#public-links)). Set to `false` to turn the feature off for the whole instance: no link can be made, the buttons disappear, and the links already made stop answering. |
| `AUTH_GITLAB_BASE_URL` | - | Your GitLab, e.g. `https://gitlab.example.org`. |
| `AUTH_GITLAB_CLIENT_ID` / `AUTH_GITLAB_CLIENT_SECRET` | - | The GitLab application's ID and secret. |
| `AUTH_ALLOWED_EMAIL_DOMAINS` | - | Comma-separated email domains allowed to sign in (`example.org,example.com`). The email must be verified by GitLab. |
| `AUTH_GITLAB_ALLOWED_GROUPS` | - | Comma-separated GitLab group paths (`org/team`). Members of a subgroup are admitted. Only groups the user joined directly are seen (`groups_direct` claim). |
| `AUTH_ALLOW_ANY_USER` | `false` | Admit any account of the identity provider. Ignored when an allowlist is set. When both allowlists are set, a user must satisfy both. With none set and this off, the backend refuses to start. |
| `INSTANCE_ADMINS` | - | Comma-separated emails of the instance administrators. The first one to sign in becomes the owner of the `default` workspace, which holds the data that existed before workspaces, if it has no owner yet. They can also create workspaces when `WORKSPACE_CREATION=admins`. |
| `WORKSPACE_CREATION` | `any` | `any`: every signed-in user can create a workspace. `admins`: only the instance administrators. |
| `FRONTEND_URL` | first `CORS_ORIGINS` entry | Where the browser reaches the UI. The session cookie is `Secure` when it is `https://`. |
| `PUBLIC_API_URL` | `http://localhost:8000` | Where the browser reaches the API; the GitLab redirect URI is `<PUBLIC_API_URL>/auth/gitlab/callback`. |
| `SESSION_IDLE_DAYS` / `SESSION_MAX_DAYS` | `7` / `30` | A session expires after this many days without activity, and in any case after the second. |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|---|---|---|
| `NUXT_PUBLIC_BACK_URL` | `http://localhost:8000` | Backend URL as seen from the browser. |
| `NUXT_PUBLIC_SOURCE_URL` | the IRIT GitLab repository | Where the "Source code" entry of the help menu (the `?` at the bottom of the sidebar) leads. Empty hides the entry. |

### Workspaces

Everything the app stores (models, prompts, agents, datasets, experiments,
analyses, tags) belongs to a workspace, shown at `/w/<slug>` in the UI. You can
belong to several, with one role in each:

| Role | Can |
|---|---|
| `viewer` | read everything, run read-only computations (analysis previews, formula checks) |
| `editor` | also create, edit, delete and run experiments, and make or withdraw public links |
| `owner` | also manage members, invitation links and API keys, rename, archive and delete the workspace |

The interface follows the role: a viewer sees every page but is offered no way to
create, edit, delete or run anything; the main buttons stay visible but disabled,
with a tooltip saying who may use them, while menu items, bulk actions and
shortcuts are left out. An archived workspace is read-only for everyone. The API
enforces the same rules whatever the interface shows.

Someone who is not a member gets a 404 for the workspace and for any id inside
it: they cannot tell whether it exists. An archived workspace is read-only. A
workspace always keeps at least one owner who can still sign in: the last one
cannot leave or step down (an owner whose account was deactivated does not count).

Owners manage the workspace in **Settings**:

- **Members** - change a role, remove someone, or add a person who has already
  signed in once, by email. Anyone can leave a workspace; the last owner cannot.
- **Invitation links** - a link gives the *viewer* or *editor* role to anyone
  who opens it (they sign in first, with an account the allowlists admit). It
  works for 1, 7 or 30 days, or until it is revoked, and counts the people who
  joined through it. The link is shown only when it is created; only a hash of
  it is kept.
- **LLM provider keys** - a workspace can store its own API key for a provider.
  Runs use it instead of the instance's key, which remains the fallback. Keys
  are encrypted with `ENCRYPTION_KEY`; only their last four characters are shown
  again. Each key has its own rate limit (`<PROVIDER>_MAX_RPS`), so workspaces
  with their own keys do not slow each other down, while those sharing the
  instance's key do. Self-hosted providers (Ollama) are set for the whole
  instance, never per workspace.
- **Archive** - the workspace becomes read-only, its runs in progress stop, and
  its keys and invitation links are deleted. An owner can reopen it (the keys
  must be set again) or delete it: that removes everything in it, files
  included, after typing its identifier.

Members can also be managed from the command line (see below).
Each workspace has its own folder of datasets and results: a workspace can only
read the files it owns.

Experiments run inside the API process, so the backend must be a single process
(one uvicorn worker). When it restarts, the runs it was running are marked
*interrupted* and the queue is emptied: run them again from the UI.

### Public links

An editor or owner can give anyone a **read-only link** to an experiment, a batch,
an analysis or a study (**Share** on its page). Whoever has the link reads it in
the app's own pages, with no account.

- **What it opens**: the item and what lies strictly below it (an experiment's
  executions, a batch's experiments, the executions an analysis compares,
  everything a study gathers), with prompts, models, the dataset rows processed
  and the results file. **Never**: notes, authors, tags, the rest of the
  workspace, API keys. The reader cannot change anything.
- **Live**: the link shows the item as it is now. There is one active link per
  item, shared by all editors: whoever stops sharing, or makes a new link, ends
  the old one for everybody. Deleting the item ends it too.
- **Security**: the link is a 128-bit random token, so treat it like a document
  link anyone can open. It appears in access logs. The public routes have **no
  rate limiting** (an analysis link recomputes its metrics on every request): rate
  limit `/shared/` in your reverse proxy if the instance is exposed, and have it
  send `Referrer-Policy: no-referrer` and `X-Robots-Tag: noindex` for `/s/*`.
- **Turn it off**: `PUBLIC_SHARING_ENABLED=false`.

### Managing users and workspaces

Users are created when they first sign in. To block someone, or to cut a
session short:

```bash
docker compose exec backend uv run python manage.py users list
docker compose exec backend uv run python manage.py users deactivate <email|id>
docker compose exec backend uv run python manage.py users activate <email|id>
docker compose exec backend uv run python manage.py users logout <email|id>
```

```bash
docker compose exec backend uv run python manage.py workspaces list
docker compose exec backend uv run python manage.py workspaces members <slug>
docker compose exec backend uv run python manage.py workspaces add-member <slug> <email|id> <viewer|editor|owner>
docker compose exec backend uv run python manage.py workspaces remove-member <slug> <email|id>
```

Deactivating a user closes their sessions at once. The allowlists are only
checked at sign-in: someone who stops matching them keeps their session until
it expires, unless you deactivate them.

## Sample datasets

- `backend/scripts/sample_datasets/mohler_dataset.csv` - the short-answer grading dataset from
  Mohler, Bunescu and Mihalcea, *Learning to Grade Short Answer Questions using
  Semantic Similarity Measures and Dependency Graph Alignments* (ACL 2011).
- `backend/scripts/sample_datasets/diff_gt_2_mohler_dataset.csv` - the subset of the above where the
  two human graders disagree by more than 2 points.

## Development notes

- Backend lint: `uvx ruff check backend`.
- Frontend lint: `pnpm lint` in `frontend/` (ESLint with `@antfu/eslint-config`).
- Results files are written to `<DATA_DIR>/workspaces/<id>/results/` and referenced (by
  a path relative to that folder) from the `experimentexecution` table. With Docker
  Compose `DATA_DIR` is the `maestro-data` volume.
- Database migrations use [Alembic](https://alembic.sqlalchemy.org) and run on
  startup (`alembic upgrade head`). After changing `backend/tables.py`, generate
  a migration, review it, and check there is no drift:

  ```bash
  docker compose exec backend uv run alembic revision --autogenerate -m "describe the change"
  docker compose exec backend uv run alembic check
  ```

- The pages a public link opens are the app's own pages, served again under
  `/s/<token>/...` by a `pages:extend` hook in `frontend/nuxt.config.ts`, from the list
  `SHARED_RESOURCES` in `frontend/app/utils/workspacePath.ts`. The dev server reads that
  list when it starts: restart it after changing the list. On the API side, the routes a
  link can call are the `READABLE` allowlist in `backend/api/shared.py`; a test fails if
  one is added elsewhere.
- The tests run on PostgreSQL, in a separate `<database>_test` database that is
  created on first use (or set `TEST_DATABASE_URL`). They never touch your data.

### Deleting items that are still used

Deleting a model or a prompt version clears it from the agents, experiment
configurations and history that referenced it. An agent or a dataset still used
by an experiment cannot be deleted (HTTP 409).
