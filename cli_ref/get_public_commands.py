#!/usr/bin/env python
"""
Get list of public (non-hidden) CLI commands for documentation generation.

Inspects Click commands and options to extract structured metadata for documentation generation.

Usage:
    # Print function names to console
    python get_public_commands.py

    # Print function names with source file and line number (tab-separated)
    python get_public_commands.py --with-source

    # Write command info with source locations to JSON file
    python get_public_commands.py --output-json commands_with_source.json
"""
import argparse
import click
import inspect
import json
from wandb.cli.cli import cli
from typing import Dict, Tuple, Optional, List, Iterator

def classify_option(param: click.Option) -> str:
    """
    Classify boolean options into more specific categories for documentation purposes.
    
    Returns one of:
        - "boolean-flag"
        - "boolean-dual-flag"
        - "boolean-value"
        - "other"

    Where "boolean-flag" is a simple flag (e.g. --verbose), "boolean-dual-flag" is a flag that has both positive and negative forms (e.g. --feature / --no-feature), "boolean-value" is an option that takes a boolean value (e.g. --enable-feature true/false), and "other" is any other type of option.
    """
    if param.is_flag:
        if param.secondary_opts:
            return "boolean-dual-flag"
        return "boolean-flag"

    if isinstance(param.type, click.types.BoolParamType):
        return "boolean-value"

    return "other"


def inspect_command(command: click.Command) -> Dict[str, List[Dict]]:
    """
    Inspect a Click command and return structured option and argument metadata.
    """
    options = []
    arguments = []

    for param in command.params:
        if isinstance(param, click.Option):
            option_info = {
                "name": param.name,
                "description": param.help or "",
                "opts": param.opts,
                "secondary_opts": param.secondary_opts,
                "default": param.default,
                "required": param.required,
                "hidden": param.hidden,
                "classification": classify_option(param),
                "type": type(param.type).__name__,
                "help": param.help or "",
            }
            options.append(option_info)
        elif isinstance(param, click.Argument):
            arg_info = {
                "name": param.name,
                "type": type(param.type).__name__,
                "default": param.default,
                "required": param.required,
                "nargs": param.nargs,
            }
            arguments.append(arg_info)

    return {"options": options, "arguments": arguments}

def get_command_source_file_info(cmd) -> Tuple[Optional[str], Optional[int]]:
    """Get the source file and line number for a Click command.

    Args:
        cmd: A Click command object

    Returns:
        Tuple of (source_file, line_number) or (None, None) if not found
    """
    if not cmd.callback:
        return None, None

    try:
        # Unwrap decorated functions to get the original
        unwrapped = inspect.unwrap(cmd.callback)
        source_file = inspect.getfile(unwrapped)
        _, start_line = inspect.getsourcelines(unwrapped)
        return source_file, start_line
    except Exception:
        return None, None


def build_command_info(name: str, cmd: click.Command) -> Dict:
    """Build metadata dict for a single Click command, recursing into groups."""
    func_name = cmd.callback.__name__ if cmd.callback else name
    cmd_metadata = inspect_command(cmd)
    source_file, line_number = get_command_source_file_info(cmd)

    info = {
        'name': name,
        'func_name': func_name,
        'description': cmd.help.split("Examples:")[0].strip() if "Examples:" in (cmd.help or "") else (cmd.help or ""),
        'examples': cmd.help.split("Examples:")[-1].strip() if "Examples:" in (cmd.help or "") else "",
        'usage': click.Context(cmd, info_name=name).get_usage().split("Usage:")[-1].strip() if cmd else "",
        'source_file': source_file,
        'line_number': line_number,
        "is_click_group": isinstance(cmd, click.Group),
        "options": cmd_metadata["options"],
        "arguments": cmd_metadata["arguments"],
    }

    # If this command is a Group, recursively build info for subcommands
    if isinstance(cmd, click.Group):
        ctx = click.Context(cmd, info_name=name)
        subcommands = {}
        for sub_name in cmd.list_commands(ctx):
            sub_cmd = cmd.get_command(ctx, sub_name)
            if sub_cmd is None:
                continue
            if getattr(sub_cmd, 'hidden', False):
                continue
            subcommands[sub_name] = build_command_info(sub_name, sub_cmd)
        info["subcommands"] = subcommands

    return info


def get_public_commands_with_source():
    """Return public commands with their source file and line number.

    Returns:
        Dict mapping func_name -> {name, func_name, source_file, line_number, is_click_group, options, arguments, subcommands?}
    """
    commands = getattr(cli, 'commands', {})
    result = {}

    for name, cmd in commands.items():
        if not getattr(cmd, 'hidden', False):
            func_name = cmd.callback.__name__ if cmd.callback else name
            result[func_name] = build_command_info(name, cmd)
    return result

def get_public_commands():
    """Return list of public command function names (excluding hidden commands)."""
    return list(get_public_commands_with_source().keys())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Get list of public CLI commands for documentation generation."
    )
    parser.add_argument(
        "--output-json",
        metavar="FILE",
        help="Write command info with source locations to JSON file"
    )
    parser.add_argument(
        "--with-source",
        action="store_true",
        help="Print commands with source file and line number (tab-separated)"
    )
    args = parser.parse_args()

    if args.output_json:
        # Write to JSON file
        commands = get_public_commands_with_source()
        with open(args.output_json, 'w', encoding='utf-8') as f:
            json.dump(commands, f, indent=2)
        print(f"Wrote {len(commands)} commands to {args.output_json}\n")

    elif args.with_source:
        # Print commands with source file and line number to console
        # Does not save to file, just for debugging purposes.
        # Format: func_name \t line_number \t source_file
        for cmd in get_public_commands_with_source().values():
            print(f"{cmd['func_name']}\t{cmd['line_number']}\t{cmd['source_file']}")

    else:
        # Default: just print function names
        for cmd in get_public_commands():
            print(cmd)
