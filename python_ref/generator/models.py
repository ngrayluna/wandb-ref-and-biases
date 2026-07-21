"""Data models for the Python SDK docs generator."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ExportedName:
    """A public name exported by a package module."""

    public_name: str
    source_module: str | None = None
    source_name: str | None = None
    declared_in_all: bool = False
    config_namespace: str = ""


@dataclass(frozen=True, slots=True)
class ArgumentDoc:
    """Documentation for a callable argument."""

    name: str
    description: str = ""
    internal_use: bool = False


@dataclass(frozen=True, slots=True)
class ReturnDoc:
    """Documentation for a return value."""

    type_name: str = ""
    description: str = ""


@dataclass(frozen=True, slots=True)
class RaisesDoc:
    """Documentation for a raised exception."""

    name: str
    description: str


@dataclass(frozen=True, slots=True)
class PropertyDoc:
    """Documentation for a documented property or attribute."""

    name: str
    description: str = ""
    returns: str = ""
    internal_use: bool = False


@dataclass(frozen=True, slots=True)
class ClassAttributeDoc:
    """Documentation for an attribute listed in a class docstring."""

    name: str
    type_name: str = ""
    description: str = ""
    internal_use: bool = False


@dataclass(frozen=True, slots=True)
class MethodDoc:
    """Documentation for a public method."""

    name: str
    description: str = ""
    qualname: str = ""
    signature: str | None = None
    source_file: str = ""
    line_number: int | None = None
    arguments: list[ArgumentDoc] = field(default_factory=list)
    returns: list[ReturnDoc] = field(default_factory=list)
    examples: str = ""
    raises: list[RaisesDoc] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FunctionDoc:
    """Documentation for a public function."""

    name: str
    qualname: str = ""
    defining_module: str | None = None
    kind: str = ""
    description: str = ""
    examples: str = ""
    source_file: str = ""
    line_number: int | None = None
    import_statement: str = ""
    signature: str | None = None
    arguments: list[ArgumentDoc] = field(default_factory=list)
    returns: list[ReturnDoc] = field(default_factory=list)
    raises: list[RaisesDoc] = field(default_factory=list)
    internal_use: bool = False


@dataclass(frozen=True, slots=True)
class ClassDoc:
    """Documentation for a public class."""

    public_name: str
    qualname: str = ""
    defining_module: str | None = None
    internal_use: bool = False
    ignore_init: bool = False
    kind: str = ""
    description: str = ""
    examples: str = ""
    source_file: str = ""
    line_number: int | None = None
    import_statement: str = ""
    signature: str | None = None
    arguments: list[ArgumentDoc] = field(default_factory=list)
    attributes: list[ClassAttributeDoc] = field(default_factory=list)
    properties: list[PropertyDoc] = field(default_factory=list)
    methods: list[MethodDoc] = field(default_factory=list)
    raises: list[RaisesDoc] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ExportedObjectDoc:
    """Documentation for a public exported object that is not a class or callable."""

    name: str
    kind: str = ""
    description: str = ""
    source_file: str = ""
    line_number: int | None = None
    import_statement: str = ""
    internal_use: bool = False


@dataclass(frozen=True, slots=True)
class ParsedDocstring:
    """A light-weight parsed docstring."""

    description: str = ""
    examples: str = ""
    ignore_init: bool = False
    arguments: list[ArgumentDoc] = field(default_factory=list)
    attributes: list[ClassAttributeDoc] = field(default_factory=list)
    returns: list[ReturnDoc] = field(default_factory=list)
    raises: list[RaisesDoc] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DocumentableObject:
    """A normalized, inspect-derived representation of a public object."""

    public_name: str
    obj: Any
    kind: str
    defining_module: str | None
    qualname: str | None
    signature: str | None
    docstring: str | None
    source_module: str | None
    source_name: str | None
    declared_in_all: bool
    source_file: str | None
    line_number: int | None
    import_statement: str
