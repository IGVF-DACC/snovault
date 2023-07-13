FROM public.ecr.aws/docker/library/python:3.11.4-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE 1

ENV PYTHONUNBUFFERED 1

ENV VIRTUAL_ENV=/opt/venv

RUN useradd -u 1444 -m snovault

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    git \
    graphviz \
    libjpeg-dev \
    libmagic-dev \
    libpq-dev \
    libsqlite3-dev \
    make \
    zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv $VIRTUAL_ENV

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN chown -R snovault:snovault $VIRTUAL_ENV

WORKDIR /scripts

COPY --chown=snovault:snovault scripts .

RUN chmod -R +x /scripts

WORKDIR /snovault

COPY --chown=snovault:snovault setup.cfg pyproject.toml ./

COPY --chown=snovault:snovault src/snovault/__init__.py src/snovault/__init__.py

USER snovault

RUN python -m pip install --upgrade pip setuptools

RUN pip install -e .[dev]

COPY --chown=snovault:snovault . .

EXPOSE 6543

ENTRYPOINT ["/scripts/pyramid/entrypoint.sh"]

CMD ["/scripts/pyramid/run-development.sh"]
