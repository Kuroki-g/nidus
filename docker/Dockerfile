# syntax=docker/dockerfile:1
# check=error=true
FROM 3.14.3-slim-bookworm

ENV TRANSFORMERS_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1
ENV HF_HOME=/app/models

COPY ./models/static-embedding-japanese /app/models/hub/models--hotchpotch--static-embedding-japanese

RUN --mount=type=cache,target=/root/.cache/huggingface \
    python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('hotchpotch/static-embedding-japanese', local_files_only=True)"
