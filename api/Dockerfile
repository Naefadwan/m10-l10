FROM python:3.11-slim

WORKDIR /app

# Cache dependency install layer — copy requirements before the rest of
# the source so a code-only change does not re-run pip install.


# Download the spaCy English model required by /extract.
RUN python -m spacy download en_core_web_sm

# Copy the full repo (build context is the repo root per lab guide Task 5).
COPY . .

EXPOSE 8000

# Run uvicorn as `api.main:app` (package-relative imports require this).
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
