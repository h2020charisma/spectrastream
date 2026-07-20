FROM python:3.12-slim AS requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without=dev --without-hashes

FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=requirements-stage /tmp/requirements.txt /tmp/

RUN sed -i 's/^-e //' /tmp/requirements.txt \
    && pip install --no-cache-dir --upgrade -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY ./src /app

WORKDIR /app

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://127.0.0.1:8501/stream/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.baseUrlPath=/stream"]
