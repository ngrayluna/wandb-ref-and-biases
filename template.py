"""
Templates for generating MDX documentation files for Click commands."""

## Template for individual functions
mdx_function_template = """---
title: {name}
---

{import_statements}
{github_path}

{signature}

## Description

{description}

{arguments_section}

{returns_section}

{raises_section}

{examples_section}

"""

## Template for Python classes

mdx_class_template = """---
title: {name}
---

{import_statements}
{github_path}

{signature}

## Description

{description}

{arguments_section}

{properties_section}

{methods_section}

"""