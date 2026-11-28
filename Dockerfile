FROM ghcr.io/astral-sh/uv:0.13.10@sha256:a3ea1357342c1a4bf9a0c53a3deb1b55379aefa037338d8113d5771efa01774f AS uv

FROM python:3.15.2-alpine3.24@sha256:0f9552bb28711333da16915ec146f5e6bb44a7fdac9ced15dc17c2e0206346dd AS builder

COPY --from=uv /uv /uvx /bin/
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0
ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_PROGRESS=1

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --all-extras --no-install-project --no-dev --no-editable

COPY pyproject.toml uv.lock LICENSE README.md ./
COPY src/ ./src/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-extras --no-dev --no-editable


FROM python:3.15.2-alpine3.24@sha256:0f9552bb28711333da16915ec146f5e6bb44a7fdac9ced15dc17c2e0206346dd
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

RUN apk upgrade --no-cache \
    && python -m pip uninstall --root-user-action=ignore -y pip \
    && rm -rf /usr/local/lib/python3.*/ensurepip \
              /usr/local/lib/python3.*/idlelib \
              /usr/local/lib/python3.*/tkinter \
              /usr/local/lib/python3.*/turtledemo \
              /usr/local/include \
              /usr/local/bin/idle* /usr/local/bin/pydoc* /usr/local/bin/python*-config \
    && apk add --no-cache ca-certificates-bundle \
    && apk del --no-cache apk-tools \
    && addgroup -g 10001 appuser \
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
