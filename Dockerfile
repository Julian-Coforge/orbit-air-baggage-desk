# STRETCH GOAL 4: a Docker image that runs the app and the tests.
#
# Build:      docker build -t orbit-air .
# Run app:    docker run --rm orbit-air --now 2026-11-02T14:01:00 report
# Run tests:  docker run --rm --entrypoint pytest orbit-air -q
FROM python:3.12-slim

WORKDIR /app

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY pyproject.toml db.py claims.py main.py seed_claims.csv ./
COPY tests ./tests

ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
