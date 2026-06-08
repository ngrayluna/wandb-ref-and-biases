# W&B CLI Documentation Generator

Generate MDX reference documentation for [W&B CLI commands](https://github.com/wandb/wandb/tree/main/wandb/cli) from source.

## Usage

Specify the `wandb` GitHub release tag to generate docs for:

```bash
./generate_cli.sh <release_tag>
```

Example:

```bash
./generate_cli.sh v0.18.3
```

If no release tag is provided, the script uses the existing `./wandb/` directory as-is (useful for local testing).

Optionally specify a directory to copy the markdown files to:

```bash
bash ./generate_cli.sh v0.26.0 docs/models/ref/cli
```

## How it works

1. Clones or updates the `wandb/wandb` repo to `./wandb/` and checks out the specified release tag.
2. Introspects the Click CLI to discover all public (non-hidden) commands, arguments, options, and subcommands. Writes structured metadata to `source_info.json`.
3. Generates one MDX file per command using templates, with GitHub source links, usage blocks, argument/option tables, and examples.
4. Organizes subcommand files into directories matching their Click group hierarchy.
5. (Optionally) Recursively copy the markdown files to the specified directory.

Output is written to `./output/`.

## Files

| File | Description |
|------|-------------|
| `generate_cli.sh` | Shell entrypoint that orchestrates the pipeline |
| `get_public_commands.py` | Introspects Click commands and extracts structured metadata to JSON |
| `source_info.json` | Generated JSON with command metadata (options, arguments, descriptions, source locations, etc.) |
| `create_mdx_file.py` | Reads `source_info.json` and generates MDX files using templates from `cli_doc_template.py` |
| `cli_doc_template.py` | MDX string templates for individual commands and group landing pages |
| `sort_markdown.py` | Moves subcommand MDX files into directories matching their Click group hierarchy |