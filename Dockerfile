FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv

FROM python:3.15.2-alpine3.24@sha256:2b4b04f31a4a009c1fadf7ce9338471f288488199cf43dcd1af71f244ea550aa AS builder

COPY --from=uv /uv /uvx /bin/
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


FROM python:3.15.2-alpine3.24@sha256:2b4b04f31a4a009c1fadf7ce9338471f288488199cf43dcd1af71f244ea550aa
LABEL org.opencontainers.image.title="LibreNMS MCP Server" \
      org.opencontainers.image.description="MCP server for LibreNMS management" \
      org.opencontainers.image.url="https://github.com/mhajder/librenms-mcp" \
      org.opencontainers.image.documentation="https://github.com/mhajder/librenms-mcp#readme" \
      org.opencontainers.image.authors="Mateusz Hajder" \
      org.opencontainers.image.source="https://github.com/mhajder/librenms-mcp" \
      org.opencontainers.image.vendor="Mateusz Hajder" \
      org.opencontainers.image.licenses="MIT" \
      io.modelcontextprotocol.server.name="io.github.mhajder/librenms-mcp"
ENV PYTHONUNBUFFERED=1

RUN addgroup -g 10001 appuser \
    && adduser -D -u 10001 -G appuser appuser

COPY --from=builder /app/.venv /app/.venv

WORKDIR /app

USER 10001:10001

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK \
  --interval=15s \
  --timeout=10s \
  --start-period=5s \
  --retries=3 \
  CMD ["python", "-m", "librenms_mcp.healthcheck"]

ENV MCP_TRANSPORT=http
ENV MCP_HTTP_HOST=0.0.0.0
ENV MCP_HTTP_PORT=8000

EXPOSE 8000

ENTRYPOINT ["librenms-mcp"]
