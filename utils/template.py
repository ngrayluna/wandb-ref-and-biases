"""
Templates for generating MDX documentation files for Python SDK reference docs.
These templates are used to create structured documentation for functions, classes, and CLI commands based on metadata extracted from the source code.
"""
## Template for individual functions (not Class methods)## 
FUNCTION_TEMPLATE = """---
title: {name}()
kind: {kind}
namespace: {namespace}
---

{import_statements}
{github_path}

{function_title}
{signature}

{description}

{arguments_section}

{returns_section}

{raises_section}

{examples_section}

"""

## Template for Class objects ##

CLASS_TEMPLATE = """---
title: {name}
kind: {kind}
namespace: {namespace}
---

{import_statements}
{github_path}

{class_title}

{description}

{signature}

{arguments_section}

{attributes_section}

{examples_section}

"""


CLASS_PROPERTIES_PAGE_TEMPLATE = """---
title: {name} properties
sidebarTitle: Properties
page_kind: class-properties
parent_slug: {parent_slug}
kind: {kind}
namespace: {namespace}
---

{class_title}

{properties_section}

"""


CLASS_METHODS_PAGE_TEMPLATE = """---
title: {name} methods
sidebarTitle: Methods
page_kind: class-methods
parent_slug: {parent_slug}
kind: {kind}
namespace: {namespace}
---

{class_title}

{methods_section}

"""

## Template for individual Click commands (commands that do not have subcommands) and Click command groups (commands that have subcommands) are imported from cli_doc_template.py to avoid circular imports.

CLI_COMMAND_TEMPLATE = """---
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

## Template for Click command groups (commands that have subcommands) is imported from cli_doc_template.py to avoid circular imports.

CLI_GROUP_TEMPLATE = """---
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
