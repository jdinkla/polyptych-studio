# TextClient API Reference

`TextClient` provides multi-provider text generation with structured output, automatic fallback chains, and usage logging. Located in `src/polyptych/client.py`.

## Basic Usage

```python
from polyptych.client import TextClient
from polyptych.models import TaskI0Output

client = TextClient(provider="gemini")

# Structured output (returns a Pydantic model)
result = client.generate_structured(
    prompt="Analyze this essay...",
    response_schema=TaskI0Output,
    model="gemini-2.5-flash-preview-05-20",
    system_instruction="You are an analyst.",
    task="i0",
)

# Plain text output
text = client.generate_text(
    prompt="Summarize this...",
    model="gemini-2.5-flash-preview-05-20",
    task="i0",
)
```

## Constructor

```python
TextClient(
    provider: str = "gemini",
    fallback: list[str] | None = None,
    api_key: str | None = None,
    usage_log: Path | None = Path("usage.jsonl"),
    model_resolver: Callable[[str, str], str] | None = None,
    thinking_budget_resolver: Callable[[str, str], int | None] | None = None,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider` | `str` | `"gemini"` | Primary provider name |
| `fallback` | `list[str] \| None` | `None` | Fallback chain. `None` = auto (all other providers). `[]` or `["none"]` = disabled |
| `api_key` | `str \| None` | `None` | API key for the primary provider only |
| `usage_log` | `Path \| None` | `Path("usage.jsonl")` | JSONL usage log path. `None` disables logging |
| `model_resolver` | `Callable[[str, str], str] \| None` | `None` | `(task_name, provider_name) -> model_string` |
| `thinking_budget_resolver` | `Callable[[str, str], int \| None] \| None` | `None` | `(task_name, provider_name) -> budget_tokens` |

`GeminiTextClient` is a backward-compatible alias for `TextClient`.

## `generate_structured()`

```python
def generate_structured(
    self,
    prompt: str,
    response_schema: type[T],       # T bound to pydantic.BaseModel
    model: str,
    system_instruction: str | None = None,
    max_output_tokens: int | None = None,
    task: str | None = None,
) -> T
```

Returns a validated Pydantic model instance. Raises `ContentBlockedError` if all providers (primary + fallbacks) block the request.

The `task` parameter is used for fallback model resolution and usage logging — it does not affect generation behavior.

## `generate_text()`

```python
def generate_text(
    self,
    prompt: str,
    model: str,
    system_instruction: str | None = None,
    task: str | None = None,
) -> str
```

Returns raw text. Same fallback and logging behavior as `generate_structured()`.

## Fallback Chain

```
Primary provider
     │
     ├── success → return result
     │
     └── ContentBlockedError
              │
              ├── log to blocked-requests.jsonl
              │
              ├── fallback[0]: resolve model → try → success? return
              ├── fallback[1]: resolve model → try → success? return
              ├── fallback[N]: ...
              │
              └── all blocked → re-raise ContentBlockedError
```

For each fallback provider, the `model_resolver` callback is called with `(task, fallback_provider_name)`. If it returns `None` (no configuration for that provider/task), the fallback is skipped.

When `fallback=None` (default), the chain includes all providers from `list_text_providers()` except the primary. When `fallback=[]` or `fallback=["none"]`, fallback is disabled.

## `ContentBlockedError`

```python
class ContentBlockedError(ValueError):
    def __init__(self, message: str, block_reason: str | None = None):
        self.block_reason = block_reason
```

Raised when a provider blocks a request due to content policy. `block_reason` values vary by provider:

| Provider | Possible values |
|----------|----------------|
| Gemini | Safety category string from `prompt_feedback.block_reason` |
| OpenAI | `"content_filter"`, `"refusal"` |
| xAI | `"content_filter"`, `"refusal"` |
| Anthropic | `"refusal"` (when `stop_reason == "refusal"`) |

## `TextGenerationResult`

```python
@dataclass
class TextGenerationResult:
    provider: str                             # e.g. "gemini"
    model: str                                # model string used
    duration_s: float                         # wall-clock seconds
    prompt_token_count: int | None = None
    candidates_token_count: int | None = None
    total_token_count: int | None = None
    thoughts_token_count: int | None = None   # Gemini extended thinking only
    extra: dict = field(default_factory=dict)
```

Returned by provider implementations alongside the generated content. Token fields are `None` when the provider does not report them.

## `BaseTextProvider` Interface

```python
class BaseTextProvider(ABC):
    def __init__(self, api_key: str | None = None): ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        model: str,
        system_instruction: str | None = None,
        max_output_tokens: int | None = None,
        thinking_budget: int | None = None,
    ) -> tuple[T, TextGenerationResult]: ...

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        model: str,
        system_instruction: str | None = None,
        thinking_budget: int | None = None,
    ) -> tuple[str, TextGenerationResult]: ...
```

Provider implementations return a `tuple[result, TextGenerationResult]`. The `TextClient` unwraps this — callers of `TextClient` receive just the result.

API keys are resolved via `_get_api_key(env_keys)`: checks the constructor `api_key` parameter first, then iterates environment variable names. Raises `ValueError` if none found.

## Available Providers

| Provider | Class | Env vars | Structured output |
|----------|-------|----------|-------------------|
| `gemini` | `GeminiTextProvider` | `GOOGLE_API_KEY`, `GEMINI_API_KEY` | Native JSON schema |
| `openai` | `OpenAITextProvider` | `OPENAI_API_KEY` | `json_schema` response format |
| `xai` | `XAITextProvider` | `XAI_API_KEY` | `json_schema` with prompt fallback |
| `anthropic` | `AnthropicTextProvider` | `ANTHROPIC_API_KEY` | Prompt-injected schema |
| `vertex` | `VertexTextProvider` | `GOOGLE_CLOUD_PROJECT` (+ optional `GOOGLE_CLOUD_LOCATION`) | Native JSON schema (inherits from Gemini) |

`vertex` uses Application Default Credentials instead of API keys and is excluded from the auto-fallback chain. `xai` uses the OpenAI SDK with a custom `base_url`.

Anthropic is the only provider that supports `thinking_budget` — when set, it enables extended thinking mode with the specified token budget.

## Usage Logging

### `usage.jsonl`

Each successful generation appends one JSON line:

```json
{
  "timestamp": "2026-02-28T12:34:56.789000+00:00",
  "provider": "gemini",
  "model": "gemini-2.5-flash-preview-05-20",
  "method": "generate_structured",
  "task": "i0",
  "duration_s": 4.312,
  "prompt_token_count": 8421,
  "candidates_token_count": 1203,
  "total_token_count": 9624
}
```

`method` is `"generate_structured"` or `"generate_text"`. Token fields are omitted when `None`.

### `blocked-requests.jsonl`

Written alongside `usage.jsonl` when a request is blocked:

```json
{
  "timestamp": "2026-02-28T12:34:56.789000+00:00",
  "provider": "gemini",
  "model": "gemini-2.5-flash-preview-05-20",
  "task": "i0",
  "block_reason": "HARM_CATEGORY_DANGEROUS",
  "message": "LLM returned empty response ...",
  "prompt": "<full prompt text>"
}
```

The full prompt is logged for debugging blocked requests.

## Model Tier Resolution

Model selection follows a three-level resolution order:

1. **`--model` flag** — overrides everything, forces all tiers to use this model
2. **`$POLYPTYCH_MODEL` env var** (deprecated alias `$SLIDE_GEN_MODEL`) — same effect as `--model`
3. **`model_config.yaml`** — per-task tier assignment (`fast` or `thinking`), per-provider model strings

```python
# model_config.py
def resolve_model(config: ModelConfig, task_name: str, provider: str = "gemini") -> str:
    tier = config.tasks.get(task_name, "fast")    # default to fast
    return config.providers[provider][tier]        # KeyError if provider not configured
```

The `ModelConfig` dataclass also provides `resolve_max_output_tokens(task_name)` and `resolve_thinking_budget(task_name, provider)`. Thinking budget always returns `None` for non-Anthropic providers and for tasks on the `fast` tier.

## `repair_truncated_json()`

Located in `src/polyptych/providers/base.py`. Attempts to recover JSON that was truncated at the model's `max_output_tokens` limit.

Algorithm:
1. Try `json.loads()` — return immediately if valid.
2. Walk the text tracking string escapes and nesting depth.
3. Close any unclosed string literal.
4. Strip trailing commas.
5. Close all open `{` and `[` brackets in reverse order.
6. Try `json.loads()` on the repaired text.
7. Print a warning to stderr on success. Return `None` if repair fails.

Used internally by all provider implementations in `generate_structured()`.

## Related Documentation

- [CLI Reference](cli-reference.md) — `--model`, `--text-provider`, `--text-fallback` flags
- [System Overview](../explanation/system-overview.md) — how TextClient fits into the pipeline
- [Pipeline Tier Optimization](pipeline-tier-optimization.md) — per-task fast/thinking tier assignments
