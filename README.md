# Lab 10 — FastAPI + Next.js Recipe Service

Build a typed, containerized FastAPI backend that wraps spaCy NER, the
W9B deterministic NL→Cypher mapper, and an M8-style RAG pipeline, plus
a containerized Next.js frontend that consumes those endpoints.

> Read the full Lab guide on the cohort site:
> <https://LevelUp-Applied-AI.github.io/aispire-14005-pages/modules/module-10/c17e29dd>

## Setup

The Module 10 package install lives in the Reading. If you have not
already installed the M10 packages, complete that install first.

Backend:

```bash
cd api
pip install -r requirements.txt
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
cp .env.example .env  # edit values
```

Frontend:

```bash
cd web
cp .env.local.example .env.local
npm ci
```

## Run

Bring up Neo4j and Weaviate (from the M9/M8 Compose stacks, or any
running instances reachable at your configured URLs), then:

```bash
cd api && uvicorn main:app --reload --port 8000   # terminal 1
cd web && npm run dev                              # terminal 2
```

Open `http://localhost:3000`.

Lab-level Compose (api + web only — assumes Neo4j and Weaviate are
running externally):

```bash
docker compose up -d --build
```

## Verify

```bash
pytest tests/backend -v
cd web && npm run build && npm run test:e2e
```

Both must pass before submission.

## Submission

Fork-and-submit per the M8+ pattern. See `FORK-SUBMIT.md`.

---

## License

This repository is provided for educational use only. See
[LICENSE](LICENSE) for terms. You may clone and modify this repository
for personal learning and practice, and reference code you wrote here
in your professional portfolio. Redistribution outside this course is
not permitted.
