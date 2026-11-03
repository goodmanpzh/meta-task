FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y git procps

COPY setup_repo.sh /tmp/setup_repo.sh
RUN bash /tmp/setup_repo.sh \
    && rm /tmp/setup_repo.sh \
    && rm -rf /tmp/golden /tmp/golden-bare /tmp/bundles /tmp/main-bundle.bundle \
       /tmp/metadata_* /tmp/stash_* /tmp/*.txt /tmp/*.pack

WORKDIR /app/project
