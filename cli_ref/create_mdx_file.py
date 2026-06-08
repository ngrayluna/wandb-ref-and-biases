"""Script to generate MDX documentation files for Click commands based on extracted metadata.

Usage: python create_mdx_file.py --json-file source_info_debug.json
"""
import argparse
import re
import json
from pathlib import Path
import textwrap
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.template import CLI_COMMAND_TEMPLATE, CLI_GROUP_TEMPLATE
from utils.markdown import format_github_button, github_import_statement


def format_code_block(content: str) -> str:
    """Convert indented '$ wandb ...' lines into fenced bash code blocks.

    Before:
        Verify the currently configured W&B instance.

            $ wandb verify --host https://my-wandb-instance.com

    After:
        Verify the currently configured W&B instance.

        ```bash
        wandb verify --host https://my-wandb-instance.com
        ```
    """
    def replace_match(match):
        command = match.group(1).strip()
        return f"\n```bash\n{command}\n```"

    return re.sub(r'^\s*\$ (.+)$', replace_match, content, flags=re.MULTILINE)


def format_description(content: str) -> str:
    """Clean up a CLI command description for MDX output.

    Applies the following transformations:
    - Strips leading/trailing whitespace
    - Removes common leading indentation (from docstring formatting)
    - Converts indented '$ command' lines into fenced bash code blocks
    """
    content = textwrap.dedent(content).strip()
    content = format_code_block(content)
    return content


_TYPE_DISPLAY_NAMES = {
    "StringParamType": "STR",
    "IntParamType": "INT",
    "IntRange": "INT",
    "FloatParamType": "FLOAT",
    "FloatRange": "FLOAT",
    "BoolParamType": "BOOL",
    "Path": "PATH",
}

def normalize_type(raw_type: str, classification: str) -> str:
    """Map Click type class names to clean display names."""
    if classification in ("boolean-flag", "boolean-dual-flag"):
        return "BOOL Flag"
    return _TYPE_DISPLAY_NAMES.get(raw_type, raw_type)


def format_argument_row(arg: dict) -> str:
    """Format a single argument as a markdown table row.

    Args:
        arg: Dict containing argument metadata, including 'name', 'type',
        'default', 'required', and 'classification'.

    Returns:
        Markdown table row string.
    """
    name = arg['name']
    arg_type = normalize_type(arg['type'], arg.get('classification', ''))
    required = arg['required']
    return f"| `{name}` | {arg_type} | {required} |"


def format_option_row(opt: dict) -> str:
    """Format a single option as a markdown table row.
    
    Args:
        opt: Dict containing option metadata, including 'opts', 'type',
        'description', 'default', and 'classification'.

    Returns:
        Markdown table row string.
    """
    flags = ', '.join(opt['opts'])
    opt_type = normalize_type(opt['type'], opt.get('classification', ''))
    desc = ' '.join(opt['description'].splitlines())
    default = opt['default']
    return f"| `{flags}` | {opt_type} | {desc} **Default**: {default} |"


def format_subcommand_row(command_path: list[str], sub_name: str, sub_info: dict) -> str:
    """Format a single subcommand as a markdown table row.
    
    Args:
        command_path: List of command name segments, e.g. ["server", "start"].
        sub_name: Name of the subcommand.
        sub_info: Dict of subcommand metadata.

    Returns:
        Markdown table row string.
    """
    display_name = " ".join(command_path)
    sub_slug = "-".join(command_path + [sub_name])
    sub_display = " ".join(command_path + [sub_name])
    sub_desc = sub_info.get("description", "").split("\n")[0]
    return f"| `wandb {sub_display}` | {sub_desc} |"
    # TO DO: Consider linking to subcommand MDX file if it exists, e.g.:
    #return f"| [`wandb {sub_display}`](wandb-{display_name.replace(' ', '-')}/wandb-{sub_slug}) | {sub_desc} |"


def build_examples_section(examples: str) -> str:
    """Build the Examples markdown section, or empty string if no examples."""
    if not examples or not examples.strip():
        return ""
    return f"## Examples\n\n{format_code_block(examples)}\n"


def build_arguments_section(arguments: list[dict]) -> str:
    """Build the Arguments markdown table section, or empty string if no arguments."""
    rows = [format_argument_row(arg) for arg in arguments]
    if not rows:
        return ""
    return f"## Arguments\n\n| Name | Default | Type |\n|------|---------|------|\n{chr(10).join(rows)}\n"


def build_options_section(options: list[dict]) -> str:
    """Build the Options markdown table section, or empty string if no visible options."""
    rows = [format_option_row(opt) for opt in options if not opt['hidden']]
    if not rows:
        return ""
    return f"## Options\n\n| Flag | Type | Description |\n|------|------|-------------|\n{chr(10).join(rows)}\n"


def build_subcommands_section(command_path: list[str], subcommands: dict) -> str:
    """Build the Subcommands markdown table section, or empty string if no subcommands."""
    rows = [format_subcommand_row(command_path, name, info) for name, info in subcommands.items()]
    if not rows:
        return ""
    return f"## Subcommands\n\n| Command | Description |\n|---------|-------------|\n{chr(10).join(rows)}\n"


def generate_mdx(command_info, command_path: list[str], output_dir: str, release_tag: Optional[str] = None):
    """Generate an MDX file for a command and recurse into subcommands.

    Args:
        command_info: Dict of command metadata from source_info_debug.json.
        command_path: List of command name segments, e.g. ["server", "start"].
        output_dir: Directory to write generated MDX files.
        release_tag: Git tag for GitHub URL (e.g., 'v0.18.3'). Defaults to 'main'.
    """
    description = format_description(command_info.get("description", ""))
    source_file = command_info.get("source_file", "")
    line_number = command_info.get("line_number", "")
    subcommands = command_info.get("subcommands", {})
    is_group = command_info.get("is_click_group", False)

    display_name = " ".join(command_path)
    file_slug = "-".join(command_path)

    shared_fields = dict(
        name=display_name,
        description=description,
        import_statements=github_import_statement(),
        github_path=format_github_button(source_file, line_number, release_tag),
        usage=command_info.get("usage", ""),
    )

    with open(f"{output_dir}/wandb-{file_slug}.mdx", "w", encoding="utf-8") as f:
        if is_group:
            f.write(CLI_GROUP_TEMPLATE.format(
                **shared_fields,
                subcommands_section=build_subcommands_section(command_path, subcommands),
            ))
        else:
            f.write(CLI_COMMAND_TEMPLATE.format(
                **shared_fields,
                examples_section=build_examples_section(command_info.get("examples", "")),
                arguments_section=build_arguments_section(command_info.get("arguments", [])),
                options_section=build_options_section(command_info.get("options", [])),
            ))

    # Recurse into subcommands
    for sub_name, sub_info in subcommands.items():
        generate_mdx(sub_info, command_path + [sub_name], output_dir, release_tag)


def main(args):

    ### Main logic to read source info and generate MDX files
    with open(args.source_info, 'r', encoding='utf-8') as file:
        json_file = json.load(file)

    for command_name, command_info in json_file.items():
        generate_mdx(command_info, [command_info.get("name", command_name)], args.output_dir, args.release_tag)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MDX documentation files for Click commands.")
    parser.add_argument("--source-info", default="source_info.json", help="Path to JSON file with command metadata.")
    parser.add_argument("--output-dir", default="output", help="Directory to write generated MDX files.")
    parser.add_argument("--release-tag", default=None, help="Git tag for GitHub source URLs (e.g., 'v0.18.3'). Defaults to 'main'.")
    main(parser.parse_args())
    print("MDX generation complete.")