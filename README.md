# Snovault2

The Snovault general purpose hybrid object-relational database

## Run with Docker Compose
1. Clone repository and make sure Docker is running.
2. Start services and load data inserts:
```bash
# From repository.
$ docker compose up
# Note if any dependencies have changed (e.g. switching between branches that
# rely on different versions of snovault) use the build flag as well
# to rebuild the underlying Docker image:
$ docker compose up --build
```
3. Browse at `localhost:6543`.
4. Stop services and remove data volume:
```bash
$ docker compose down -v
```

## Test with Docker Compose
Run all unit tests automatically and clean up:
```bash
$ docker compose -f docker-compose.test.yml up --exit-code-from pyramid --build
....
$ docker compose -f docker-compose.test.yml down -v
```

Run all indexer tests automatically and clean up:
```bash
$ docker-compose -f docker-compose.test-indexer.yml up --exit-code-from indexer-tests --build
....
$ docker compose -f docker-compose.test-indexer.yml down -v
```

Or run tests interactively:
1. Start `postgres` service (for use as fixture).
```bash
$ docker compose -f docker-compose.test.yml up postgres
```
2. Connect to testing environment.
```bash
# In another terminal (starts interactive container).
$ docker compose -f docker-compose.test.yml run --service-ports pyramid /bin/bash
```
3. Run tests.
```bash
# In interactive container (modify pytest command as needed).
$ pytest
```
4. Stop and clean.
```bash
docker compose down -v
```

## Automatic linting
This repo includes configuration for pre-commit hooks. To use pre-commit, install pre-commit, and activate the hooks:
```bash
pip install pre-commit==2.17.0
pre-commit install
```
Now every time you run `git commit` the automatic checks are run to check the changes you made.
