FROM python:3.14-alpine3.24 AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --all-extras --no-install-project --no-dev --no-editable

COPY pyproject.toml uv.lock LICENSE README.md ./
COPY src/ ./src/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-extras --no-dev --no-editable


FROM python:3.14-alpine3.24
LABEL org.opencontainers.image.title="LibreNMS MCP Server" \
      org.opencontainers.image.description="MCP server for LibreNMS management" \
      org.opencontainers.image.url="https://github.com/mhajder/librenms-mcp" \
      org.opencontainers.image.source="https://github.com/mhajder/librenms-mcp" \
      org.opencontainers.image.vendor="Mateusz Hajder" \
      org.opencontainers.image.licenses="MIT" \
      io.modelcontextprotocol.server.name="io.github.mhajder/librenms-mcp"
ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache ca-certificates \
    && addgroup -g 1000 appuser \
    && adduser -D -u 1000 -G appuser appuser

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

WORKDIR /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK \
  --interval=15s \
  --timeout=5s \
  --start-period=5s \
  --retries=3 \
  CMD if [ "$MCP_TRANSPORT" = "http" ]; then nc -z 127.0.0.1 "${MCP_HTTP_PORT:-8000}" || exit 1; fi

ENV MCP_TRANSPORT=http
ENV MCP_HTTP_HOST=0.0.0.0
ENV MCP_HTTP_PORT=8000

EXPOSE 8000

ENTRYPOINT ["librenms-mcp"]
