"""
Templates for generating MDX documentation files for Click commands.
"""
## Template for individual functions (not Class methods)## 
FUNCTION_TEMPLATE = """---
title: {name}
kind: {kind}
namespace: {namespace}
---

{import_statements}
{github_path}

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

{signature}

{description}

{arguments_section}

{examples_section}

{properties_section}

{methods_section}

"""