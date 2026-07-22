# W&B Reference Docs Generator

Tools for generating W&B Python SDK and CLI reference docs as MDX files.

The generators inspect the `wandb/wandb` source tree, create intermediate JSON
metadata, render MDX, and copy the final files into a sibling docs repo.

## Requirements

- Python 3.8+
- Git
- `python-frontmatter`
- A sibling `../docs` checkout if you want the scripts to copy generated files
  into the docs repo

Install the Python dependency:

```bash
pip install python-frontmatter
```

## Usage

Generate both Python SDK and CLI docs for a release tag:

```bash
./generate_docs.sh --tag v0.18.3
```

Generate only Python SDK docs:

```bash
./generate_python.sh --tag v0.18.3
```

Generate only CLI docs:

```bash
./generate_cli.sh v0.18.3
```

If no tag is provided, the scripts use an existing local `../wandb` checkout.
Generated files are written under `generated/` and copied to `../docs/models/ref/`.

## Layout

- `generate_docs.sh` - runs both generators
- `generate_python.sh` - builds Python SDK reference pages
- `generate_cli.sh` - builds CLI reference pages
- `python_ref/` - Python API discovery and MDX rendering
- `cli_ref/` - CLI command discovery and MDX rendering
- `utils/` - shared markdown and template helpers
- `tests/` - focused regression tests

