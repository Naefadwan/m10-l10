# Lab 10 — backend Dockerfile. Author this file.
#
# TODO: choose a slim Python base image so the runtime is small.
# TODO: order layers so dependency install is cached between rebuilds
#       (install requirements before copying the rest of the source).
# TODO: install the spaCy English model needed by /extract.
# TODO: expose the FastAPI port and start uvicorn against `api.main:app`
#       with the build context set to the repo root (NOT `cd api &&
#       uvicorn main:app`). The starter uses package-relative imports
#       (`from .models import Entity`), which require uvicorn to load the
#       package as `api.*` — running `uvicorn main:app` from inside the
#       `api/` directory breaks these imports with `ImportError:
#       attempted relative import with no known parent package`.
#
# See lab-guide.md "Containerization" section for the constraints the
# autograder will check.
