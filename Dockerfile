FROM python:3.12-slim as requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without=dev --without-hashes

FROM python:3.12-slim

LABEL maintainer="Luchesar ILIEV <luchesar.iliev@gmail.com>" \
      org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.description="A web-based spectra harmonization tool" \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.schema-version="1.0" \
      org.opencontainers.image.source="https://github.com/h2020charisma/spectrastream" \
      org.opencontainers.image.title="spectrastream" \
      org.opencontainers.image.url="https://github.com/h2020charisma/spectrastream/blob/main/README.md" \
      org.opencontainers.image.vendor="IDEAconsult" \
      org.opencontainers.image.version="latest"

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=requirements-stage /tmp/requirements.txt /tmp/

RUN sed -i 's/^-e //' /tmp/requirements.txt \
    && pip install --no-cache-dir --upgrade -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY ./src/spectrastream  /app

WORKDIR /app

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://127.0.0.1:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
