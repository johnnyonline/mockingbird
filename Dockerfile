FROM python:3.12

WORKDIR /app

COPY . .

RUN pip install uv && uv sync --no-dev --no-cache

ENV PATH="/app/.venv/bin:${PATH}"

ENTRYPOINT ["python", "-u", "-m", "bot"]
