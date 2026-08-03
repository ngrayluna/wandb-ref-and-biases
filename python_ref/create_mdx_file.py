"""
Generate .mdx files for Python SDK.
"""
import os
import re
import argparse
import glob
import json
from pathlib import Path
from typing import Iterable, NamedTuple, Optional
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.template import (
    CLASS_METHODS_PAGE_TEMPLATE,
    CLASS_PROPERTIES_PAGE_TEMPLATE,
    CLASS_TEMPLATE,
    FUNCTION_TEMPLATE,
)
from utils.markdown import format_github_button, github_import_statement

PAGE_SECTION_HEADING = "##"
METHOD_SECTION_HEADING = "#####"


class ClassMdxPages(NamedTuple):
    """Generated MDX pages for a class."""

    main: str
    properties: str
    methods: str


def build_markdown_section(
    heading: str,
    body: str,
    heading_marker: str = PAGE_SECTION_HEADING,
) -> str:
    """Build a markdown section with a heading, or empty string if no body."""
    body = body.strip("\n")
    if not body.strip():
        return ""

    return f"{heading_marker} {heading}\n\n{body}"


def join_markdown_blocks(blocks: Iterable[str]) -> str:
    """Join non-empty markdown blocks with consistent spacing."""
    return "\n\n".join(
        block.strip("\n")
        for block in blocks
        if block and block.strip()
    )


def build_description_section(description: str) -> str:
    """Build the Description markdown section, or empty string if no description."""
    if not description:
        return ""
    return f"\n\n{description}\n\n"

def build_function_arguments_section(arguments: list[dict]) -> str:
    """Build the Args section for a standalone function page."""
    return build_argument_list_section(
        heading="Args",
        arguments=arguments,
        heading_marker=PAGE_SECTION_HEADING,
    )


def build_class_constructor_arguments_section(arguments: list[dict]) -> str:
    """Build the Args section for constructor args on the main class page."""
    return build_argument_list_section(
        heading="Args",
        arguments=arguments,
        heading_marker=PAGE_SECTION_HEADING,
    )


def build_class_method_arguments_section(arguments: list[dict]) -> str:
    """Build the Arguments subsection for a class method entry."""
    return build_argument_list_section(
        heading="Arguments",
        arguments=arguments,
        heading_marker=METHOD_SECTION_HEADING,
    )


def build_argument_list_section(
    heading: str,
    arguments: list[dict],
    heading_marker: str,
) -> str:
    """Build an argument list section with the requested heading level."""
    if not arguments:
        return ""

    formatted_arguments = "".join(
        format_argument_row(arg)
        for arg in arguments
        if not internal_use_only(arg)
    )
    if not formatted_arguments:
        return ""

    return build_markdown_section(
        heading,
        formatted_arguments,
        heading_marker,
    )

def build_attributes_section(attributes: list[dict]) -> str:
    """Build the Attributes markdown section, or empty string if no attributes."""
    if not attributes:
        return ""

    formatted_attributes = "".join(
        format_attribute_row(attr)
        for attr in attributes
        if not internal_use_only(attr)
    )
    if not formatted_attributes:
        return ""
    return build_markdown_section("Attributes", formatted_attributes)

def build_returns_section(returns: list[dict]) -> str:
    """Build the Returns markdown section, or empty string if no return value."""
    return build_markdown_section("Returns", format_returns_body(returns))


def build_method_returns_section(returns: list[dict]) -> str:
    """Build the method Returns markdown section, or empty string if no return value."""
    return build_markdown_section(
        "Returns",
        format_returns_body(returns),
        METHOD_SECTION_HEADING,
    )


def format_returns_body(returns: list[dict]) -> str:
    """Format return metadata shared by function and method docs."""
    # TODO: Check logic for handling multiple return values. Currently, only
    # the first return value is used.
    type_name = returns[0].get("type_name") if returns else ""
    description = returns[0].get("description") if returns else ""

    if not returns:
        return ""
    if description and description.startswith("_"):
        return ""
    
    if type_name == "" or type_name == "return":
        section = f"{description}"
    else:
        section = f"`{type_name}`: {description}"

    return section

def build_raises_section(raises: list[dict]) -> str:
    """Build the Raises markdown section, or empty string if no exceptions raised."""
    if not raises:
        return ""
    formatted_raises = "".join(format_raises_row(raise_) for raise_ in raises)
    return build_markdown_section("Raises", formatted_raises)

def build_method_raises_section(raises: list[dict]) -> str:
    """Build the Raises markdown section, or empty string if no exceptions raised."""
    if not raises:
        return ""
    formatted_raises = "".join(format_raises_row(raise_) for raise_ in raises)
    return build_markdown_section("Raises", formatted_raises, METHOD_SECTION_HEADING)

def build_examples_section(examples: str) -> str:
    """Build the Examples markdown section, or empty string if no examples."""
    if not examples:
        return ""
    return build_markdown_section("Examples", examples)

def build_method_examples_section(examples: str) -> str:
    """Build the Examples markdown section, or empty string if no examples."""
    if not examples:
        return ""
    return build_markdown_section("Examples", examples, METHOD_SECTION_HEADING)

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

def build_class_methods_body(methods: list[dict]) -> str:
    """Build the body for a class methods page, or empty string if no methods."""
    if not methods:
        return ""

    formatted_methods = join_markdown_blocks(
        format_method_entry(method)
        for method in methods
        if is_public_method_doc(method)
    )
    if not formatted_methods:
        return ""

    return formatted_methods


def build_class_properties_body(properties: list[dict]) -> str:
    """Build the body for a class properties page, or empty string if no properties.

    Properties marked for internal use only (identified by 'lazydoc' in description) are
    filtered out and not included in the output.
    """
    if not properties:
        return ""

    formatted_properties = "".join(
        format_property_row(prop)
        for prop in properties
        if not internal_use_only(prop)
    )
    if not formatted_properties:
        return ""
    return formatted_properties.strip("\n")


def format_output_slug(name: str) -> str:
    """Format an object name the same way generated MDX filenames are normalized."""
    return name.lower()



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
    # TODO: Consider making this a configurable list of paths to ignore, or
    # using a more robust method for determining internal vs. public modules.
    filepaths_to_ignore = [
        "/data_types/base_types/",
        "/pydantic/",
        "/_pydantic/",
        "/apis/attrs.py",
    ]
    if any(ignore_path in source_file for ignore_path in filepaths_to_ignore):
        return False

    return True


def is_public_method_doc(method: dict) -> bool:
    """Return whether a method doc should appear on the class methods page."""
    return not internal_use_only(method) and validate_source_file(
        method.get("source_file", "")
    )


def format_method_heading(method: dict) -> str:
    """Format a method entry heading."""
    return f"### <kbd>method</kbd> {method.get('qualname', '')}()"


def format_method_entry(method: dict) -> str:
    """Format a single method entry for the Methods page."""
    description = method.get("description", "")
    signature = build_signature_block(method.get("signature", ""))
    arguments = build_class_method_arguments_section(method.get("arguments", []))
    returns = build_method_returns_section(method.get("returns", []))
    raises = build_method_raises_section(method.get("raises", []))
    examples = build_method_examples_section(method.get("examples", ""))
    return join_markdown_blocks(
        [
            format_method_heading(method),
            description,
            signature,
            arguments,
            returns,
            raises,
            examples,
        ]
    )

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
    return (
        "lazydoc" in doc_entry.get("description", "")
        or doc_entry.get("name", "").startswith("_")
        or doc_entry.get("qualname", "").startswith("_")
    )


def generate_class_mdx_content(
    doc_entry: dict,
    release_tag: Optional[str] = None,
) -> ClassMdxPages:
    """Generate MDX content for a class object using the class template."""
    ignore_init = doc_entry.get("ignore_init", False)
    public_name = doc_entry.get("public_name", "")
    parent_slug = format_output_slug(public_name)
    class_main = CLASS_TEMPLATE.format(
        name=doc_entry.get("public_name", ""),
        kind=doc_entry.get("kind", ""),
        namespace=doc_entry.get("defining_module", ""),
        class_title=format_class_page_title(doc_entry.get("filename", "")),
        description=build_description_section(doc_entry.get("description", "")),
        signature=(
            "" if ignore_init else build_signature_block(doc_entry.get("signature", ""))
        ),
        arguments_section=(
            ""
            if ignore_init
            else build_class_constructor_arguments_section(
                doc_entry.get("arguments", [])
            )
        ),
        returns_section=build_returns_section(doc_entry.get("returns", "")),
        attributes_section=build_attributes_section(doc_entry.get("attributes", [])),
        examples_section=build_examples_section(doc_entry.get("examples", "")),
        import_statements=github_import_statement(),
        github_path=format_github_button(
            source_file=doc_entry.get("source_file", ""),
            line_number=doc_entry.get("line_number", 0),
            release_tag=release_tag,
        ),
    )

    properties_section = build_class_properties_body(doc_entry.get("properties", []))
    class_properties = ""
    if properties_section:
        class_properties = CLASS_PROPERTIES_PAGE_TEMPLATE.format(
            name=public_name,
            parent_slug=parent_slug,
            kind=doc_entry.get("kind", ""),
            namespace=doc_entry.get("defining_module", ""),
            class_title=format_class_page_title(doc_entry.get("filename", "")),
            properties_section=properties_section,
        )

    methods_section = build_class_methods_body(doc_entry.get("methods", []))
    class_methods = ""
    if methods_section:
        class_methods = CLASS_METHODS_PAGE_TEMPLATE.format(
            name=public_name,
            parent_slug=parent_slug,
            kind=doc_entry.get("kind", ""),
            namespace=doc_entry.get("defining_module", ""),
            class_title=format_class_page_title(doc_entry.get("filename", "")),
            methods_section=methods_section,
        )

    return ClassMdxPages(class_main, class_properties, class_methods)

def generate_function_mdx_content(doc_entry: dict, release_tag: Optional[str] = None) -> str:
    """Generate MDX content for a function object using the function template."""
    return FUNCTION_TEMPLATE.format(
        name=doc_entry.get("name", ""),
        kind=doc_entry.get("kind", ""),
        namespace=doc_entry.get("defining_module", ""),
        function_title=format_function_page_title(doc_entry.get('filename', '')),
        description=build_description_section(doc_entry.get("description", "")),
        signature=build_signature_block(doc_entry.get("signature", "")),
        arguments_section=build_function_arguments_section(
            doc_entry.get("arguments", [])
        ),
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

    output_dir = args.output_dir

    for filename in glob.glob(os.path.join(args.source_info, '*.json')):
        with open(filename, 'r', encoding='utf-8') as file:
            json_file = json.load(file)

        item_key = next(iter(json_file), None)
        if not item_key:
            print(f"No items found in {filename}, skipping.")
            continue

        doc_entry = json_file[item_key]
        if doc_entry.get("kind") == "class":
            class_pages = generate_class_mdx_content(doc_entry, release_tag=args.release_tag)

            if class_pages.main:
                class_main_filename = f"{output_dir}/{item_key}.{doc_entry.get('defining_module', '').replace('.', '_')}.mdx"
                print(f"Creating MDX content for {item_key} at {class_main_filename}")
                with open(class_main_filename, 'w', encoding='utf-8') as f:
                    f.write(class_pages.main)

                if class_pages.properties:
                    class_properties_filename = f"{output_dir}/{item_key}-properties.{doc_entry.get('defining_module', '').replace('.', '_')}.mdx"
                    print(f"Creating MDX content for {item_key} properties at {class_properties_filename}")
                    with open(class_properties_filename, 'w', encoding='utf-8') as f:
                        f.write(class_pages.properties)

                if class_pages.methods:
                    class_methods_filename = f"{output_dir}/{item_key}-methods.{doc_entry.get('defining_module', '').replace('.', '_')}.mdx"
                    print(f"Creating MDX content for {item_key} methods at {class_methods_filename}")
                    with open(class_methods_filename, 'w', encoding='utf-8') as f:
                        f.write(class_pages.methods)

        elif doc_entry.get("kind") == "function":
            template = generate_function_mdx_content(doc_entry, release_tag=args.release_tag)
            generated_filename = f"{output_dir}/{item_key}.{doc_entry.get('defining_module', '').replace('.', '_')}.mdx"
            print(f"Creating MDX content for {item_key} at {generated_filename}")
            with open(generated_filename, 'w', encoding='utf-8') as f:
                f.write(template)
        else:
            raise ValueError(f"Unsupported item kind: {doc_entry.get('kind')}")

        # print(f"Created MDX content for {item_key}")

    print("MDX generation complete.\n") 


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MDX documentation files for Click commands.")
    parser.add_argument("--source-info", required=True, help="Path to JSON directory with command metadata.")
    parser.add_argument("--output-dir", default="output", help="Directory to write generated MDX files.")
    parser.add_argument("--release-tag", default=None, help="Git tag for GitHub source URLs (e.g., 'v0.18.3'). Defaults to 'main'.")
    main(parser.parse_args())   
