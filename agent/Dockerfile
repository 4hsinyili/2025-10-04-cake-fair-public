FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV APP_HOME=/app

ENV PATH="/usr/bin/uv:/root/.local/bin:$PATH"

# Copy local code to the container image.
COPY . /app/agent
WORKDIR $APP_HOME/agent

# Enable keyring authentication
# Set the username for the index
RUN uv venv --python 3.12 
RUN uv sync

CMD ["/app/agent/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3002"]
