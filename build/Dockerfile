FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV APP_HOME=/app

ENV PATH="/usr/bin/uv:/root/.local/bin:$PATH"

COPY . /app/build
WORKDIR $APP_HOME/build

# install git
RUN apt-get update && apt-get install -y git
# Enable keyring authentication
# Set the username for the index
RUN uv venv --python 3.12 
RUN uv sync
