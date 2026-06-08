"""
Check if a Click command belongs to a Group. If it does, create a directory
for the group and place the commands inside it.

Do not move the top level Group commands, only the subcommands. For example,
if we have a group "docker" with subcommands "run" and "build", create a
directory "wandb-docker" and move "wandb-docker-run.md" and
"wandb-docker-build.md" into "wandb-docker". The "wandb-docker.md" file 
should remain in the top level output directory.

Python commands that are Click groups have "is_click_group": true in the
output of get_public_commands_with_source(). We can use this to determine
which commands are groups and create directories for them. 
"""

import argparse
import json
import os

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Get list of public CLI commands for documentation generation."
    )
    parser.add_argument(
        "--source-info",
        type=str,
        default="public_commands.json",
        help="Path to output JSON file with public command information.",
    )
    parser.add_argument(
        "--output-markdown",
        type=str,
        default="output",
        help="Path to output directory for markdown files.",
    )
    args = parser.parse_args()

    print(f"Sorting markdown files in directory: {args.output_markdown}\nUsing source info from: {args.source_info}")

    # Load existing source info (already generated and enriched by earlier pipeline steps)
    with open(args.source_info, "r") as f:
        public_commands = json.load(f)

    root_dir = args.output_markdown

    def sort_group(command_info, parent_dir, command_path):
        """Recursively create directories for groups and move subcommand files.

        Args:
            command_info: Dict with command metadata (including 'subcommands' for groups).
            parent_dir: Directory where this group's folder should be created.
            command_path: List of command name segments, e.g. ["artifact", "cache"].
        """
        subcommands = command_info.get("subcommands", {})
        if not subcommands:
            return

        group_slug = "-".join(command_path)
        group_dir = os.path.join(parent_dir, f"wandb-{group_slug}")
        os.makedirs(group_dir, exist_ok=True)

        for sub_name, sub_info in subcommands.items():
            sub_path = command_path + [sub_name]
            sub_slug = "-".join(sub_path)
            filename = f"wandb-{sub_slug}.mdx"
            # Files are always generated flat in the root output directory
            old_path = os.path.join(root_dir, filename)

            if os.path.exists(old_path):
                new_path = os.path.join(group_dir, filename)
                os.rename(old_path, new_path)
                print(f"  Moved {filename} -> wandb-{group_slug}/")

            # Recurse into nested groups
            sort_group(sub_info, group_dir, sub_path)

    for cmd_info in public_commands.values():
        if cmd_info.get("is_click_group"):
            sort_group(cmd_info, root_dir, [cmd_info["name"]])