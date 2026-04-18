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
    return f"## Args:\n\n{arguments}"

def build_returns_section(returns: str) -> str:
    """Build the Returns markdown section, or empty string if no return value."""
    return f"## Returns:\n\n{returns}"

def build_raises_section(raises: list[dict]) -> str:
    """Build the Raises markdown section, or empty string if no exceptions raised."""
    return f"## Raises:\n\n{raises}"

def build_examples_section(examples: str) -> str:
    """Build the Examples markdown section, or empty string if no examples."""
    return f"## Examples:\n\n{examples}"

def properties_section(properties: list[dict]) -> str:
    """Build the Properties markdown section, or empty string if no visible properties."""
    return "## Properties:\n\n"


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
    import_statements = github_import_statement()

    arguments_section = build_arguments_section(arguments)
    returns_section = build_returns_section(returns)
    raises_section = build_raises_section(raises)
    examples_section = build_examples_section(examples)

    return mdx_function_template.format(
        name=name,
        #namespace=namespace,
        description=description,
        signature=signature,
        arguments_section=arguments_section,
        returns_section=returns_section,
        raises_section=raises_section,
        examples_section=examples_section,
        import_statements=import_statements,
        github_path=github_button,
    )

def main(args):

    ### Main logic to read source info and generate MDX files
    with open(args.source_info, 'r', encoding='utf-8') as file:
        json_file = json.load(file)

    item_key = next(iter(json_file), None)
    
    if json_file[item_key].get("kind") == "class":
        # template = generate_class_mdx_content()
        print("Class MDX generation not implemented yet.")
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
    print(template)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MDX documentation files for Click commands.")
    parser.add_argument("--source-info", default="source_info.json", help="Path to JSON file with command metadata.")
    parser.add_argument("--output-dir", default="output", help="Directory to write generated MDX files.")
    parser.add_argument("--release-tag", default=None, help="Git tag for GitHub source URLs (e.g., 'v0.18.3'). Defaults to 'main'.")
    main(parser.parse_args())
    print("MDX generation complete.")    