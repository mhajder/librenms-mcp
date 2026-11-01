# Contributing

Thanks for helping out. Bug reports and feature requests go through the [issue templates](https://github.com/mhajder/librenms-mcp/issues/new/choose). For security problems, follow [SECURITY.md](SECURITY.md) instead.

## Development setup

```sh
git clone https://github.com/mhajder/librenms-mcp.git
cd librenms-mcp
uv sync --group dev
uv run prek install
```

`prek install` sets up the git hooks, which run ruff, ty, typos and pytest on commit and check the commit message.

## Before opening a pull request

```sh
uv run pytest
uv run ruff check .
uv run ruff format .
uv run ty check .
```

- Add or update tests for the change.
- Update the README when you add a tool, a setting or change behavior.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/), for example `feat(tools): add device search` or `fix(config): reject blank URLs`. The changelog and the next version are generated from them.

## License

By contributing, you agree that your contributions are licensed under the project's MIT license.
