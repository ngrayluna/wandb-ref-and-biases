"""
Generate .mdx files for Python SDK.
"""
import argparse
import json
from typing import Optional

from template import mdx_function_template, mdx_class_template

def _github_button(href_links: str) -> str:
    """Add a GitHub button with the given URL.
    
    Args:
        href_links (str): URL for the GitHub button.
    """
    return '<GitHubLink url="' + href_links + '" />' + "\n\n"

def format_github_button(
    source_file: str,
    line_number: int,
    release_tag: Optional[str] = None
) -> str:
    """Build a GitHub source link button for a file.

    Args:
        source_file: Local path to source file (from inspect.getfile)
        line_number: Line number in source file
        release_tag: Git tag for GitHub URL (e.g., 'v0.18.3'). Defaults to 'main'.

    Returns:
        GitHubLink component string

    Example output URL:
        https://github.com/wandb/wandb/blob/v0.18.3/wandb/cli/cli.py#L314
    """
    # Extract repo-relative path (e.g., "wandb/cli/cli.py")
    _, sep, after = source_file.rpartition('/wandb/')
    repo_path = 'wandb/' + after if sep else source_file

    git_ref = release_tag if release_tag else "main"
    github_url = f"https://github.com/wandb/wandb/blob/{git_ref}/{repo_path}#L{line_number}"

    return _github_button(github_url)

def github_import_statement():
    """Mintlify-friendly import statement for GitHubLink component used in MDX templates."""
    return "import { GitHubLink } from '/snippets/en/_includes/github-source-link.mdx';" + "\n\n"

def build_arguments_section(arguments: list[dict]) -> str:
    """Build the Arguments markdown section, or empty string if no arguments."""
    if not arguments:
        return ""
    formatted_arguments = "".join(format_argument_row(arg) for arg in arguments)
    return f"## Args:\n\n{formatted_arguments}"

def build_returns_section(returns: list[dict]) -> str:
    """Build the Returns markdown section, or empty string if no return value."""
    if not returns:
        return ""
    formatted_returns = "".join(format_returns_row(ret) for ret in returns)
    return f"## Returns:\n\n{formatted_returns}"

def build_raises_section(raises: list[dict]) -> str:
    """Build the Raises markdown section, or empty string if no exceptions raised."""
    if not raises:
        return ""
    formatted_raises = "".join(format_raises_row(raise_) for raise_ in raises)
    return f"## Raises:\n\n{formatted_raises}"

def build_examples_section(examples: str) -> str:
    """Build the Examples markdown section, or empty string if no examples."""
    return f"## Examples:\n\n{examples}"

def build_signature_block(signature: str) -> str:
    """Build a markdown code block for the function signature."""
    if not signature:
        return ""
    formatted_signature = format_signature_block(signature)
    return f"```python\n{formatted_signature}\n```"

def build_methods_section(methods: list[dict]) -> str:
    """Build the Methods markdown section for a class, or empty string if no methods."""
    if not methods:
        return ""
    formatted_methods = "".join(format_methods_row(method) for method in methods)
    return f"## Methods:\n\n{formatted_methods}"

def build_properties_section(properties: list[dict]) -> str:
    """Build the Properties markdown section, or empty string if no visible properties."""
    if not properties:
        return ""
    formatted_properties = "".join(format_property_row(prop) for prop in properties)
    return f"## Properties:\n\n{formatted_properties}"

def format_raises_row(raise_: dict) -> str:
    """Format a single exception row for the Raises section."""
    type_name = raise_.get("type_name", "")
    description = raise_.get("description", "")
    return f"- **{type_name}**: {description}\n"

def format_methods_row(method: dict) -> str:
    """Format a single method row for the Methods section."""
    name = method.get("name", "")
    description = method.get("description", "")
    return f"### {name}\n\n{description}\n\n"

def format_property_row(property: dict) -> str:
    """Format a single property row for the Properties section."""
    name = property.get("name", "")
    description = property.get("description", "")
    return f"### {name}\n\n{description}\n\n"

def format_argument_row(argument: dict) -> str:
    """Format a single argument row for the Arguments section."""
    name = argument.get("name", "")
    description = argument.get("description", "")
    return f"- **{name}**: {description}\n"

def format_returns_row(return_value: dict) -> str:
    """Format a single return value row for the Returns section."""
    type_name = return_value.get("type_name", "")
    description = return_value.get("description", "")
    return f"- **{type_name}**: {description}\n"

def format_signature_block(signature: str) -> str:
    """Return the parameter portion of a signature as a multi-line block.

    Example input:
        "(entity: 'str | None' = None, project: 'str | None' = None) -> 'Run'"

    Example output:
        entity: 'str | None' = None,
        project: 'str | None' = None,
    """
    if not signature:
        return ""

    params_part = signature.split(") ->", maxsplit=1)[0].removeprefix("(")

    return params_part.replace(", ", ",\n")


# def generate_class_mdx_content(
#         name: str = "",
#         description: str = "",
#         signature: str = "",
#         arguments: list[dict] = None,
#         returns: str = "",
#         properties: list[dict] = None,
#         methods_section: list[dict] = None,
#         github_button: str = "",

# ):
#     """Generate MDX content for a class using the mdx_class_template."""

#     return mdx_class_template.format(
#         name=name,
#         description=description,
#         signature=build_signature_block(signature),
#         arguments_section=build_arguments_section(arguments),
#         returns_section=build_returns_section(returns),
#         properties_section=build_properties_section(properties),
#         methods_section=build_methods_section(methods_section),
#         import_statements=github_import_statement(),
#         github_path=github_button,
#     )

def generate_class_mdx_content(object: dict, release_tag: Optional[str] = None) -> str:
    return mdx_class_template.format(
        name=object.get("public_name", ""),
        description=object.get("description", ""),
        signature=build_signature_block(object.get("signature", ""),),
        arguments_section=build_arguments_section(object.get("arguments", []),),
        returns_section=build_returns_section(object.get("returns", "")),
        properties_section=build_properties_section(object.get("properties", [])),
        methods_section=build_methods_section(object.get("methods", [])),
        import_statements=github_import_statement(),
        github_path=format_github_button(
                source_file=object.get("source_file", ""),
                line_number=object.get("line_number", 0),
                release_tag=release_tag)
    )



def generate_function_mdx_content(
    name: str,
    #namespace: str,
    description: str,
    signature: str,
    arguments: list[dict],
    returns: str,
    raises: list[dict],
    examples: str,
    github_button: str,
) -> str:
    """Generate MDX content for a function using the mdx_function_template."""

    arguments_section = build_arguments_section(arguments)
    returns_section = build_returns_section(returns)
    raises_section = build_raises_section(raises)
    examples_section = build_examples_section(examples)
    signature_block = build_signature_block(signature)

    return mdx_function_template.format(
        name=name,
        #namespace=namespace,
        description=description,
        signature=signature_block,
        arguments_section=arguments_section,
        returns_section=returns_section,
        raises_section=raises_section,
        examples_section=examples_section,
        import_statements=github_import_statement(),
        github_path=github_button,
    )

def main(args):

    ### Main logic to read source info and generate MDX files
    with open(args.source_info, 'r', encoding='utf-8') as file:
        json_file = json.load(file)

    item_key = next(iter(json_file), None)
    
    if json_file[item_key].get("kind") == "class":
        object = json_file[item_key]
        template = generate_class_mdx_content(object, release_tag=args.release_tag)
    elif json_file[item_key].get("kind") == "function":
        template = generate_function_mdx_content(
            name=json_file[item_key].get("name", ""),
            #namespace=json_file[item_key].get("namespace", ""),
            description=json_file[item_key].get("description", ""),
            signature=json_file[item_key].get("signature", ""),
            arguments=json_file[item_key].get("arguments", []),
            returns=json_file[item_key].get("returns", ""),
            raises=json_file[item_key].get("raises", []),
            examples=json_file[item_key].get("examples", ""),
            github_button=format_github_button(
                source_file=json_file[item_key].get("source_file", ""),
                line_number=json_file[item_key].get("line_number", 0),
                release_tag=args.release_tag,
            )
        )
    else:
        raise ValueError(f"Unsupported item kind: {json_file[item_key].get('kind')}")

    # Loop through each command/class and generate MDX content
    print(f"Created MDX content for {item_key}:")
    with open(f"{args.output_dir}/{item_key}.mdx", 'w', encoding='utf-8') as f:
        f.write(template)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MDX documentation files for Click commands.")
    parser.add_argument("--source-info", default="source_info.json", help="Path to JSON file with command metadata.")
    parser.add_argument("--output-dir", default="output", help="Directory to write generated MDX files.")
    parser.add_argument("--release-tag", default=None, help="Git tag for GitHub source URLs (e.g., 'v0.18.3'). Defaults to 'main'.")
    main(parser.parse_args())
    print("MDX generation complete.")    