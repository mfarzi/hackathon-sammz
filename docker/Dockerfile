# Image shared by the hub's ServerApp and every hospital's ClientApp.
#
# Only the dependencies are baked in. The app itself arrives as a FAB when you
# `flwr run`, so code changes need no rebuild - which matters when the thing
# you are iterating on is a prompt.
ARG FLWR_VERSION=1.35.0
FROM flwr/superexec:${FLWR_VERSION}

USER root
RUN apt-get update \
    && apt-get -y --no-install-recommends install build-essential \
    && rm -rf /var/lib/apt/lists/*
USER app

WORKDIR /app
COPY --chown=app:app pyproject.toml .

# Strip the app's own entry so `pip install .` resolves dependencies without
# needing the source tree, which is not in the image.
RUN sed -i 's/.*flwr\[simulation\].*//' pyproject.toml \
    && python -m pip install -U --no-cache-dir .

ENTRYPOINT ["flower-superexec"]
