---
name: check-models
description: Search the web for the latest AI model names and identifiers for a provider, then compare with model_config.yaml and image_model_config.yaml
user-invocable: true
args:
  - name: provider
    description: "Provider to check: gemini, openai, xai/grok, anthropic/claude, vertex, or 'all' to check every provider. Optional — defaults to 'all' when omitted."
---

# Check Latest AI Models for a Provider

You are given a `provider` argument identifying which AI provider's models to look up. **If no argument is provided, default to `all`** (check every provider) rather than stopping to ask.

## Provider Mapping

Map the argument to a search scope. Each provider may appear in `model_config.yaml` (text/LLM tiers) and/or `image_model_config.yaml` (image model). Cover both.

| Argument            | Text entries (`model_config.yaml`) | Image entries (`image_model_config.yaml`) | Search hints                                     |
|---------------------|------------------------------------|-------------------------------------------|--------------------------------------------------|
| `gemini`            | `providers.gemini`                 | `providers.gemini`, `providers.x_gemini`  | `site:ai.google.dev` Gemini models, API ids     |
| `openai` / `gpt`    | `providers.openai`                 | `providers.openai`                        | `site:developers.openai.com` models, gpt-image (NOT `platform.openai.com` — that host blocks WebFetch with 403) |
| `xai` / `grok`      | `providers.xai`                    | `providers.xai`                           | `site:docs.x.ai` Grok / grok-imagine models — pages are often skeletal; lean on WebSearch result snippets, not WebFetch |
| `anthropic` / `claude` | `providers.anthropic`           | (none — no image gen)                     | `site:platform.claude.com` models (the old `docs.anthropic.com` URL 301-redirects to `platform.claude.com/docs/en/...`) |
| `vertex`            | `providers.vertex`                 | `providers.vertex`                        | Vertex AI model garden — Gemini ids on Vertex   |
| `all`               | all of the above                   | all of the above                          | run each provider in sequence                    |

If no argument is given, treat it as `all`. If a non-empty argument doesn't match any of the above, tell the user the valid options and stop.

## Steps

1. **Read both config files** from the repository root:
   - `model_config.yaml` — display the `fast` and `thinking` model ids for the matched provider(s) under `providers:`.
   - `image_model_config.yaml` — display the matched provider's image model id (and `x_gemini` if relevant).

   Show the current values so the user can see what's about to be compared.

2. **Search the web** for the latest available models from that provider. Use targeted queries:
   - Provider docs first: `site:ai.google.dev`, `site:developers.openai.com`, `site:platform.claude.com`, `site:docs.x.ai`, `site:cloud.google.com vertex ai`
   - General fallback: `<provider> latest AI models 2026 API model id`
   - For image entries, search specifically for image-generation model ids (e.g. `gpt-image-2 successor`, `gemini image preview latest`, `grok-imagine model id`).

3. **Fetch the relevant documentation page(s)** with WebFetch to extract actual model identifiers — not marketing names. Look for:
   - Stable model id strings (e.g. `gemini-3.1-pro`, `gpt-5.5`, `claude-opus-4-7`, `grok-4.20-reasoning`)
   - Stable vs preview/experimental distinction (entries currently using `-preview` ids should stay on previews unless a stable replacement exists)
   - Recommended / current vs deprecated status
   - For Anthropic: prefer the current Sonnet/Opus/Haiku tier ids; verify whether dated suffixes are required.

   **Known WebFetch-incompatible hosts — do not WebFetch these, use the alternative:**

   | Don't fetch                           | Use instead                                              | Why                                            |
   |---------------------------------------|----------------------------------------------------------|------------------------------------------------|
   | `platform.openai.com/docs/...`        | `developers.openai.com/api/docs/models/<id>`             | `platform.openai.com` returns 403 to WebFetch  |
   | `docs.anthropic.com/en/docs/...`      | `platform.claude.com/docs/en/docs/...` (after redirect)  | `docs.anthropic.com` 301s to `platform.claude.com`; fetch the redirect URL directly to save a round-trip |
   | `docs.x.ai/developers/models`         | WebSearch result snippets + secondary sources (Vercel AI Gateway listings, OpenRouter, release-note aggregators) | The official models page often omits exact API ids in the rendered HTML WebFetch sees |

   If a WebFetch returns 4xx, do **not** retry the same URL — switch to the alternative above (or fall back to WebSearch snippets) instead of burning more requests.

4. **Compare** fetched ids against the config files. For each entry, determine:
   - Is the current id still listed by the provider?
   - Is there a newer stable or preview successor?
   - Are there new tiers worth adding (e.g. a new "mini" / "nano" / "reasoning" model that fits `fast` or `thinking`)?

5. **Present a summary table** to the user, separated by config file. Example:

   ```
   Provider: gemini

   model_config.yaml
   Tier      Current Identifier              Latest Available                 Status
   ────      ──────────────────              ────────────────                 ──────
   fast      gemini-3-flash-preview          gemini-3-flash                   ⚠ stable available
   thinking  gemini-3.1-pro-preview          gemini-3.1-pro-preview           ✓ up to date

   image_model_config.yaml
   Entry      Current Identifier              Latest Available                 Status
   ─────      ──────────────────              ────────────────                 ──────
   gemini     gemini-3-pro-image-preview      gemini-3-pro-image-preview       ✓ up to date
   x_gemini   gemini-3.1-flash-image-preview  gemini-3.1-flash-image-preview   ✓ up to date
   ```

   Status indicators:
   - `✓ up to date` — current id is the latest recommended
   - `⚠ update available` — a newer id exists (note: stable replacing preview is also `⚠`)
   - `✗ deprecated` — current id is deprecated or removed
   - `? unknown` — couldn't determine status

6. **If updates are available**, show the exact YAML changes needed for the affected file(s) as a diff, but **do NOT apply them automatically**. Ask the user whether to apply.

## Important Notes

- `model_config.yaml` model ids are bare provider-native ids (no `provider:` prefix). Preserve that format when suggesting updates — don't introduce a routing prefix that doesn't exist in this repo.
- The `vertex` provider in this repo runs Gemini models — its ids should match what Vertex AI exposes (which sometimes lags `ai.google.dev`). Don't blindly copy ai.google.dev ids into `vertex`; verify Vertex availability.
- `x_gemini` is an experimental/secondary slot under image providers — treat it as the "next preview" line. If the main `gemini` image entry catches up, the `x_gemini` slot should point one step ahead (next preview), not the same id.
- When uncertain whether a model is newer or just differently positioned (e.g. a "mini" sibling), flag it as `? check manually` rather than recommending a change.
- The repo's resolution order is `--model` flag > `$POLYPTYCH_MODEL` env (deprecated alias `$SLIDE_GEN_MODEL`) > config tiers — config changes affect every task that didn't override, so call out high-impact swaps (especially `thinking`-tier moves) before applying.
- Prefer stable/GA models over preview when one exists. If the current entry is on a `-preview` id and a stable successor has shipped, recommend the stable id but call out behaviour differences (preview models sometimes have different output formats / token limits).
