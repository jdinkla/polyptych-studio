# Contributing to Polyptych Studio

Thanks for your interest in contributing. This project is an essay-to-visuals
generation system with two independent pipelines (slide deck and infographic)
on top of a multi-provider text/image core. Contributions that keep the
pipelines and provider surface consistent are especially welcome.

## Development setup

```bash
uv sync                  # install dependencies into .venv
just test                # run the offline unit test suite
```

The three checks CI runs (run all three before opening a PR):

```bash
uv run ruff check src/                # lint        (just lint)
uv run pyright src/                   # type-check  (just typecheck)
uv run pytest -m "not integration"    # unit tests  (just test)
```

If you don't use [`just`](https://github.com/casey/just), the commands above
are the underlying invocations.

## Provider API keys

The pipelines call third-party provider APIs (Gemini, OpenAI, xAI, Anthropic,
Vertex AI) using keys supplied via environment variables. Real `.env*` / `.envrc`
files are gitignored — never commit credentials. The unit suite runs fully
offline; only integration tests hit real APIs:

```bash
just test-integration    # opt-in, requires API keys, costs money
```

## Pull requests

- Keep the change focused; one logical change per PR.
- Add or update tests for any behaviour change. The suite runs offline with
  mocked providers — new code should too unless it is explicitly an
  `integration` test.
- Run the three checks above locally; CI runs the same.
- Update `CHANGELOG.md` under the `Unreleased` heading.
- When editing prompt templates or the `*-presets.yaml` / `*_config.yaml`
  files, keep them consistent with each other (the
  `prompt-consistency-reviewer` agent and `polyptych validate` help here).

## Reporting bugs

Open an issue with a minimal reproduction: the pipeline (`deck` / `infographic`),
the source text, the resolved `manifest.yaml`, and the full error. Please redact
API keys.

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](LICENSE), the same license that covers this project.
