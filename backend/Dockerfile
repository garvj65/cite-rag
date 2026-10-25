FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY backend ./backend
COPY scripts ./scripts
COPY eval ./eval
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
RUN useradd --create-home citerag && mkdir -p /app/eval/results && chown citerag /app/eval/results
USER citerag
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
