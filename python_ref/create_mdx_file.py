"""
Generate .mdx files for Python SDK.
"""
import os
import re
import argparse
import glob
import json
from pathlib import Path
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.template import CLASS_TEMPLATE, FUNCTION_TEMPLATE
from utils.markdown import format_github_button, github_import_statement

def build_description_section(description: str) -> str:
    """Build the Description markdown section, or empty string if no description."""
    if not description:
        return ""
    return f"## Description\n\n{description}\n\n"

def build_arguments_section(arguments: list[dict]) -> str:
    """Build the Arguments markdown section, or empty string if no arguments."""
    if not arguments:
        return ""       
    formatted_arguments = "".join(format_argument_row(arg) for arg in arguments if not internal_use_only(arg))
    if not formatted_arguments:
        return ""
    return f"## Args\n\n{formatted_arguments}"

def build_attributes_section(attributes: list[dict]) -> str:
    """Build the Attributes markdown section, or empty string if no attributes."""
    if not attributes:
        return ""

    formatted_attributes = "".join(format_attribute_row(attr) for attr in attributes if not internal_use_only(attr))
    if not formatted_attributes:
        return ""
    return f"## Attributes\n\n{formatted_attributes}"

def build_method_arguments_section(arguments: list[dict]) -> str:
    """Build the Arguments markdown section, or empty string if no arguments."""
    if not arguments:
        return ""
    formatted_arguments = "".join(format_argument_row(arg) for arg in arguments if not internal_use_only(arg))
    if not formatted_arguments:
        return ""
    return f"##### Arguments\n\n{formatted_arguments}"

def build_returns_section(returns: list[dict]) -> str:
    """Build the Returns markdown section, or empty string if no return value."""
    # TODO:  Check logic for handling multiple return values. Currently, only the first return value is used.
    type_name = returns[0].get("type_name") if returns else ""
    description = returns[0].get("description") if returns else ""

    if not returns:
        return ""
    if description and description.startswith("_"):
        return ""
    
    if type_name == "" or type_name == "return":
        section = f"{description}"
    else:
        section = f"`{type_name}`: {description}\n"

    #formatted_returns = "".join(format_returns_row(ret) for ret in returns)
    return f"## Returns\n\n{section}"

def build_raises_section(raises: list[dict]) -> str:
    """Build the Raises markdown section, or empty string if no exceptions raised."""
    if not raises:
        return ""
    formatted_raises = "".join(format_raises_row(raise_) for raise_ in raises)
    return f"## Raises\n\n{formatted_raises}"

def build_method_raises_section(raises: list[dict]) -> str:
    """Build the Raises markdown section, or empty string if no exceptions raised."""
    if not raises:
        return ""
    formatted_raises = "".join(format_raises_row(raise_) for raise_ in raises)
    return f"##### Raises\n\n{formatted_raises}"

def build_examples_section(examples: str) -> str:
    """Build the Examples markdown section, or empty string if no examples."""
    if not examples:
        return ""
    return f"## Examples\n\n{examples}"

def build_method_examples_section(examples: str) -> str:
    """Build the Examples markdown section, or empty string if no examples."""
    if not examples:
        return ""
    return f"##### Examples\n\n{examples}\n\n"

def build_signature_block(signature: str) -> str:
    """Build a markdown code block for the function signature."""
    if not signature:
        return ""
    formatted_signature = format_signature_block(signature)

    # If empty after formatting (e.g., due to filtering for internal use only),
    # return empty string to avoid rendering an empty code block
    if not formatted_signature:
        return ""

    return f"```python\n{formatted_signature}\n```"

def build_methods_section(methods: list[dict]) -> str:
    """Build the Methods markdown section for a class, or empty string if no methods."""
    if not methods:
        return ""
    formatted_methods = "".join(format_methods_row(method) for method in methods if not internal_use_only(method) and validate_source_file(method.get("source_file", "")))
    if formatted_methods == "":
        return ""

    return f"## Methods\n\n{formatted_methods}"

def build_properties_section(properties: list[dict]) -> str:
    """Build the Properties mardown section for a class, or empty string if no properties.

    Properties marked for internal use only (identified by 'lazydoc' in description) are
    filtered out and not included in the output.
    """
    if not properties:
        return ""

    formatted_properties = "".join(format_property_row(prop) for prop in properties if not internal_use_only(prop))
    if not formatted_properties:
        return ""
    return f"## Properties\n\n{formatted_properties}"

def format_raises_row(raise_: dict) -> str:
    """Format a single exception row for the Raises section."""
    name = raise_.get("name", "")
    description = raise_.get("description", "")
    return f"- `{name}`: {description}\n"


def validate_source_file(source_file: str) -> bool:
    """Check if the source file should be included based on its path. Exclude files in certain directories.
    Args:
        source_file (str): The path to the source file.
    Returns:
        bool: True if the source file should be included; False otherwise.
    """
    #TODO: Consider making this a configurable list of paths to ignore, or using a more robust method for determining internal vs. public modules.
    filepaths_to_ignore = ["/data_types/base_types/", "/pydantic/", "/_pydantic/" , "/apis/attrs.py"]
    if any(ignore_path in source_file for ignore_path in filepaths_to_ignore):
        return False

    return True


def format_methods_row(method: dict) -> str:
    """Format a single method row for the Methods section."""
    full_name = method.get("qualname", "")
    description = method.get("description", "")
    signature = build_signature_block(method.get("signature", ""))
    arguments = build_method_arguments_section(method.get("arguments", []))
    raises = build_method_raises_section(method.get("raises", []))
    examples = build_method_examples_section(method.get("examples", ""))
    return f"### <kbd>method</kbd> {full_name}()\n\n{signature}\n\n{description}\n\n{arguments}\n\n{raises}\n\n{examples}"

def format_property_row(property_doc: dict) -> str:
    """Format a single property row for the Properties section."""
    name = property_doc.get("name", "")
    description = property_doc.get("description", "")
    return f"### <kbd>property</kbd> {name}\n\n{description}\n\n"

def format_argument_row(argument: dict) -> str:
    """Format a single argument row for the Arguments section."""
    name = argument.get("name", "")
    description = argument.get("description", "")
    if not description:
        return f"- `{name}`: \n"

    return f"- `{name}`: {indent_markdown_list_item_text(description)}\n"


def format_attribute_row(attribute: dict) -> str:
    """Format a single attribute row for the Attributes section."""
    name = attribute.get("name", "")
    type_name = attribute.get("type_name", "")
    description = attribute.get("description", "")
    type_label = f" (`{type_name}`)" if type_name else ""
    if not description:
        return f"- `{name}`{type_label}: \n"

    return f"- `{name}`{type_label}: {indent_markdown_list_item_text(description)}\n"


def indent_markdown_list_item_text(text: str) -> str:
    """Indent multiline text so it stays inside its parent markdown list item."""
    lines = text.splitlines()
    if len(lines) <= 1:
        return text

    first_line, *remaining_lines = lines
    indented_lines = [first_line]
    indented_lines.extend(f"    {line}" if line else "" for line in remaining_lines)
    return "\n".join(indented_lines)


def format_signature_block(signature: str) -> str:
    """Return the signature string formatted with line breaks for readability,
    or empty string if signature is empty or filtered out for internal use only.

    Example input:
        "(entity: 'str | None' = None, project: 'str | None' = None) -> 'Run'"

    Example output:
        entity: 'str | None' = None,
        project: 'str | None' = None,
    """

    # Filter out signatures that contain 'client' parameters for
    # 'RetryingClient' objects, as these are internal and not relevant for end users.
    if "RetryingClient" in signature and "client" in signature:
        return ""

    # Remove surrounding return annotation.
    params = re.sub(r"^\((.*)\)\s*->\s*.+$", r"\1", signature)

    # Split on commas only when the next thing looks like a parameter name.
    parts = re.split(r",\s+(?=[A-Za-z_]\w*\s*:)", params)

    return ",\n".join(parts)

def format_function_page_title(name: str) -> str:
    """Format the function title for the MDX file."""
    return f"## <kbd>function</kbd> {name}"

def format_class_page_title(name: str) -> str:
    """Format the class title for the MDX file."""
    return f"## <kbd>class</kbd> {name}"


def internal_use_only(doc_entry: dict) -> bool:
    """Check if a doc entry is marked for internal use only, based on its description or name.

    Args:
        object (dict): The dictionary representing a function argument, return
            value, method, or property, which may contain a "description" key.

    Returns:
        bool: True if 'lazydoc' is found in the description, or if the name or
            qualname starts with an underscore, indicating internal use only.
    """
    return "lazydoc" in doc_entry.get("description", "") or doc_entry.get("name", "").startswith("_") or doc_entry.get("qualname", "").startswith("_")


def generate_class_mdx_content(doc_entry: dict, release_tag: Optional[str] = None) -> str:
    """Generate MDX content for a class object using the class template."""
    ignore_init = doc_entry.get("ignore_init", False)
    return CLASS_TEMPLATE.format(
        name=doc_entry.get("public_name", ""),
        kind=doc_entry.get("kind", ""),
        namespace=doc_entry.get("defining_module", ""),
        class_title=format_class_page_title(doc_entry.get("public_name", "")),
        description=build_description_section(doc_entry.get("description", "")),
        signature="" if ignore_init else build_signature_block(doc_entry.get("signature", ""),),
        arguments_section="" if ignore_init else build_arguments_section(doc_entry.get("arguments", []),),
        returns_section=build_returns_section(doc_entry.get("returns", "")),
        attributes_section=build_attributes_section(doc_entry.get("attributes", [])),
        properties_section=build_properties_section(doc_entry.get("properties", [])),
        methods_section=build_methods_section(doc_entry.get("methods", [])),
        examples_section=build_examples_section(doc_entry.get("examples", "")),
        import_statements=github_import_statement(),
        github_path=format_github_button(
                source_file=doc_entry.get("source_file", ""),
                line_number=doc_entry.get("line_number", 0),
                release_tag=release_tag)
    )


def generate_function_mdx_content(doc_entry: dict, release_tag: Optional[str] = None) -> str:
    """Generate MDX content for a function object using the function template."""
    return FUNCTION_TEMPLATE.format(
        name=doc_entry.get("name", ""),
        kind=doc_entry.get("kind", ""),
        namespace=doc_entry.get("defining_module", ""),
        function_title=format_function_page_title(doc_entry.get('name', '')),
        description=build_description_section(doc_entry.get("description", "")),
        signature=build_signature_block(doc_entry.get("signature", "")),
        arguments_section=build_arguments_section(doc_entry.get("arguments", [])),
        returns_section=build_returns_section(doc_entry.get("returns", "")),
        raises_section=build_raises_section(doc_entry.get("raises", [])),
        examples_section=build_examples_section(doc_entry.get("examples", "")),
        import_statements=github_import_statement(),
        github_path=format_github_button(
                source_file=doc_entry.get("source_file", ""),
                line_number=doc_entry.get("line_number", 0),
                release_tag=release_tag)
    )


def main(args):

    print("Generating MDX files from JSON metadata...")

    for filename in glob.glob(os.path.join(args.source_info, '*.json')):
        with open(filename, 'r', encoding='utf-8') as file:
            json_file = json.load(file)

        item_key = next(iter(json_file), None)
        if not item_key:
            print(f"No items found in {filename}, skipping.")
            continue

        doc_entry = json_file[item_key]
        if doc_entry.get("kind") == "class":
            template = generate_class_mdx_content(doc_entry, release_tag=args.release_tag)
        elif doc_entry.get("kind") == "function":
            template = generate_function_mdx_content(doc_entry, release_tag=args.release_tag)
        else:
            raise ValueError(f"Unsupported item kind: {doc_entry.get('kind')}")

        print(f"Created MDX content for {item_key}")
        output_dir = args.output_dir
        with open(f"{output_dir}/{item_key}.{doc_entry.get('defining_module', '').replace('.', '_')}.mdx", 'w', encoding='utf-8') as f:
            f.write(template)

    print("MDX generation complete.\n") 


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MDX documentation files for Click commands.")
    parser.add_argument("--source-info", required=True, help="Path to JSON directory with command metadata.")
    parser.add_argument("--output-dir", default="output", help="Directory to write generated MDX files.")
    parser.add_argument("--release-tag", default=None, help="Git tag for GitHub source URLs (e.g., 'v0.18.3'). Defaults to 'main'.")
    main(parser.parse_args())   
