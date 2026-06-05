"""
Templates for generating MDX documentation files for Click commands."""

## Template for individual Click commands (commands that do not have subcommands)
mdx_template = """---
title: wandb {name}
---

{import_statements}
{github_path}

## Usage

```bash
{usage}
```

## Description

{description}

{examples_section}

{arguments_section}

{options_section}
"""

## Template for Click command groups (commands that have subcommands)

mdx_group_template = """---
title: wandb {name}
---

{import_statements}
{github_path}

## Usage

```bash
{usage}
```

## Description

{description}

{subcommands_section}
"""