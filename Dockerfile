FROM python:3.14-alpine3.23 AS builder

RUN pip install --root-user-action=ignore --no-cache-dir --upgrade pip \
    && pip install --root-user-action=ignore --no-cache-dir uv

ENV UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --all-extras --no-install-project --no-dev

COPY pyproject.toml uv.lock LICENSE README.md run_server.py ./
COPY src/ ./src/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-extras --no-dev


FROM python:3.14-alpine3.23
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

COPY --from=builder --chown=appuser:appuser /app /app

WORKDIR /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK \
  --interval=15s \
  --timeout=5s \
  --start-period=5s \
  --retries=3 \
  CMD sh -c 'P="{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"health-check\",\"version\":\"1.0.0\"}}}"; eval "wget -q -O - --post-data='"'"'$P'"'"' --header='"'"'Content-Type: application/json'"'"' --header='"'"'Accept: application/json, text/event-stream'"'"' $([ -n \"$MCP_HTTP_BEARER_TOKEN\" ] && echo \"--header='"'"'Authorization: Bearer $MCP_HTTP_BEARER_TOKEN'"'"'\") http://127.0.0.1:8000/mcp" 2>&1 | grep -q "\"result\"" && exit 0 || exit 1'

ENV MCP_TRANSPORT=http
ENV MCP_HTTP_HOST=0.0.0.0
ENV MCP_HTTP_PORT=8000

EXPOSE 8000

ENTRYPOINT ["librenms-mcp"]
