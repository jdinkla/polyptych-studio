# polyptych justfile
#
# Pipeline runs use named presets (image-presets.yaml / pipeline-presets.yaml).
# Typical call:
#   just gen infographic sources/x.md --output-dir generated/x \
#       --style prompts/style-transfer/infographic/semi-flat-vector.md \
#       --image-preset openai-low
#
# Available image presets:    gem, gem-2k, openai-low, openai-medium,
#                             openai-high, xai
# Available pipeline presets: see pipeline-presets.yaml

# --- Dev ---

[group('dev')]
[doc("Show available commands")]
default:
    @just --list --unsorted

[group('dev')]
[doc("Install dependencies using uv")]
install:
    uv sync

[group('dev')]
[doc("Show polyptych help")]
help:
    uv run polyptych --help

[group('dev')]
[doc("Run unit tests (excludes integration tests)")]
test:
    uv run pytest -m "not integration" tests/

[group('dev')]
[doc("Run integration tests (requires API keys)")]
test-integration:
    uv run pytest -m integration tests/ -s

[group('dev')]
[doc("Run all tests (unit + integration)")]
test-all:
    uv run pytest tests/ -s

[group('dev')]
[doc("Run tests with coverage report")]
coverage:
    uv run pytest --cov=src --cov-report=term --cov-report=html -m "not integration" tests/

[group('dev')]
[doc("Type check with pyright")]
typecheck:
    uv run pyright src/

[group('dev')]
[doc("Format code with ruff")]
fmt:
    uv run ruff format src/

[group('dev')]
[doc("Lint code with ruff")]
lint:
    uv run ruff check src/

[group('dev')]
[doc("Validate task YAML outputs against Pydantic schemas")]
validate DIR *ARGS:
    uv run polyptych validate {{DIR}} {{ARGS}}

[group('dev')]
[doc("Clean PDF artifacts from a source markdown file")]
clean-source FILE *ARGS:
    uv run polyptych clean-source {{FILE}} {{ARGS}}

[group('dev')]
[doc("Remove generated prompts, images, and task files from a directory")]
clean DIR:
    @rm -rf {{DIR}}/prompts/* {{DIR}}/images/*
    @rm -f {{DIR}}/task*.yaml

# --- Generation (use --image-preset / --pipeline-preset for flag bundles) ---

[group('gen')]
[doc("Run a pipeline (slide or infographic). Example: just gen infographic sources/x.md --output-dir generated/x --image-preset openai-low")]
gen PIPELINE +ARGS:
    uv run polyptych {{PIPELINE}} {{ARGS}}

[group('gen')]
[doc("Run the slide deck pipeline (passthrough to `polyptych deck`)")]
deck +ARGS:
    uv run polyptych deck {{ARGS}}

[group('gen')]
[doc("Run the infographic pipeline (passthrough to `polyptych infographic`)")]
infographic +ARGS:
    uv run polyptych infographic {{ARGS}}

# --- Image generation (pixbridge CLI) ---

[group('image')]
[doc("Run image generation CLI")]
image-gen *args:
    uv run pixbridge generate {{args}}

[group('image')]
[doc("List all AI providers for image generation")]
providers:
    uv run pixbridge providers

[group('image')]
[doc("List available style transfer presets")]
style-list:
    uv run pixbridge style-transfer --list-styles

[group('image')]
[doc("Apply style transfer to a single image")]
style-transfer IMAGE STYLE:
    uv run pixbridge style-transfer {{IMAGE}} --style {{STYLE}}

[group('image')]
[doc("Run style consistency check")]
style-check STYLE PROVIDER="gemini" COUNT="5":
    uv run pixbridge consistency-check {{STYLE}} --provider {{PROVIDER}} --count {{COUNT}}

[group('image')]
[doc("Check images in a directory for integrity issues")]
image-check DIR:
    uv run pixbridge check {{DIR}}

# --- PDF ---

[group('pdf')]
[doc("Collect a slide deck's images into a PDF (requires ImageMagick)")]
create-pdf DIR FILENAME="deck.pdf":
    @cd {{DIR}}/images && magick * {{FILENAME}}

[group('pdf')]
[doc("Show paragraph IDs for a text file")]
count-paragraphs FILE:
    python3 scripts/count-paragraphs.py {{FILE}}

# --- Release ---

[group('release')]
[doc("Bump version, build dist, and print the publish command. VERSION = X.Y.Z or major/minor/patch")]
release VERSION:
    uv run python scripts/release.py {{VERSION}}
