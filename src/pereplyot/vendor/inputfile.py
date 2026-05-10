#!/usr/bin/env python3
"""JSON-based input file parser for hierarchical document definitions.

This module provides a typed, validated parser for input files that define
a document structure with either:
    - Flat: a list of chapters directly under the document, or
    - Hierarchical: parts, each containing a list of chapters.

Example (flat):
    {
        "title": "My Book",
        "chapters": [
            {"files": ["intro.txt"]},
            {"number": 2, "name": "The Fall", "files": ["fall.txt"]}
        ]
    }

Example (hierarchical):
    {
        "title": "My Book",
        "parts": [
            {
                "name": "Genesis",
                "chapters": [
                    {"files": ["genesis1.txt"]},
                    {"files": ["genesis2.txt"]}
                ]
            }
        ]
    }

Example parser usage:
    from inputfile import Document

    # Parse a JSON input file
    doc = Document.from_json("path/to/input.json")

    # Access data
    print(doc.title)
    for part in doc.parts:
        print(f"Part: {part.name}")
        for chapter in part.chapters:
            print(f"  Chapter {chapter.number}: {chapter.name}")
            for file in chapter.files:
                print(f"    {file.path}")

    # Optional fields
    if doc.author:
        print(f"Author: {doc.author}")

    # Custom metadata
    custom = doc.metadata.get("custom_key")
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Union, Any
import random

# ============================================================================
# Helper functions
# ============================================================================


def random_digit_string(x: int) -> str:
    """
    Generate a string of random digits of length x.
    (for generating unique ids)

    Args:
        x: The desired length of the output string.

    Returns:
        A string of length x where each character is a random digit '0'-'9'.
    """
    result = ""
    for _ in range(x):  # repeat x times
        digit = str(random.randint(0, 9))  # convert integer 0-9 to string
        result = result + digit  # append to the result
    return result


def resolve_base(
    raw_root: Any, json_parent: Path, parent_base: Optional[Path] = None
) -> Path:
    """
    Resolve a root value to an absolute base Path.

    Args:
        raw_root: Value from JSON (None, empty string, relative path, or absolute path)
        json_parent: Path to JSON file's parent directory (ultimate fallback)
        parent_base: Optional pre-resolved base for relative resolution (e.g., Document.root)

    Returns:
        Absolute Path to use as base for chapter resolution (never None)
    """
    # No root provided → fallback to JSON parent
    if not raw_root:
        return parent_base if parent_base is not None else json_parent

    root_path = Path(raw_root)

    # Absolute root → use as-is
    if root_path.is_absolute():
        return root_path

    # Relative root → resolve against parent_base if provided, else JSON parent
    base = parent_base if parent_base is not None else json_parent
    return (base / root_path).resolve()


# ============================================================================
# Data structures
# ============================================================================


@dataclass
class FileRef:
    """Reference to a single source file within a chapter.

    Attributes:
        path: Path to the file (Parser will resolve relative to Document.root).
        id: Optional id (defaults to random 5 digit integer string)
        name: Optional display name (overrides the filename in reports).
        parent (Optional[Chapter]): Back-reference to parent chapter.
            Set automatically by Document.from_json().
    """

    path: Path
    id: Optional[str] = field(default_factory=lambda: random_digit_string(5))
    name: Optional[str] = None
    parent: Optional["Chapter"] = None

    def __post_init__(self) -> None:
        if not self.path or str(self.path).strip() == "":
            raise ValueError("FileRef path cannot be empty")

    def __str__(self) -> str:
        """User-friendly string representation."""
        if self.name:
            return f"{self.name} ({self.path})"
        return str(self.path)


@dataclass
class Chapter:
    """A single chapter within a part or directly under a document.

    Attributes:
        number: Chapter number (e.g., 1, 2, 3).
        files: List of file references in this chapter.
        id: Optional id (defaults to random 5 digit integer string)
        _name: Optional internal name storage. Access via `name` property.
        parent (Optional[Union[Part, Document]]): Back-reference to parent part or document.
            Set automatically by Document.from_json().
    """

    number: int
    files: list[FileRef]
    id: Optional[str] = field(default_factory=lambda: random_digit_string(5))
    _name: Optional[str] = field(default=None, repr=False)
    parent: Optional[Union["Part", "Document"]] = None

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError(f"Chapter number must be positive, got {self.number}")
        if not self.files:
            raise ValueError(f"Chapter {self.number} must have at least one file")

    def __str__(self) -> str:
        """User-friendly string representation."""
        file_count = len(self.files)
        files_text = "file" if file_count == 1 else "files"
        return f"Chapter {self.number}: {self.name} ({file_count} {files_text})"

    @property
    def name(self) -> str:
        """Return chapter name, or 'Chapter X' if not set."""
        return self._name or f"Chapter {self.number}"

    @name.setter
    def name(self, value: Optional[str]) -> None:
        """Set chapter name (can be None to use default)."""
        self._name = value


@dataclass
class Part:
    """A top-level division containing multiple chapters.

    Attributes:
        number: Part number (e.g., 1, 2, 3).
        chapters: List of chapters in this part.
        id: Optional id (defaults to random 5 digit integer string)
        _name: Optional internal name storage. Access via `name` property.
        parent (Optional[Document]): Back-reference to parent document.
            Set automatically by Document.from_json().
    """

    number: int
    chapters: list[Chapter]
    root: Optional[Path] = None
    id: Optional[str] = field(default_factory=lambda: random_digit_string(5))
    _name: Optional[str] = field(default=None, repr=False)
    parent: Optional["Document"] = None

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError(f"Part number must be positive, got {self.number}")
        if not self.chapters:
            raise ValueError(f"Part {self.number} must have at least one chapter")

    def __str__(self) -> str:
        """User-friendly string representation."""
        chapter_count = len(self.chapters)
        chapters_text = "chapter" if chapter_count == 1 else "chapters"
        return f"Part {self.number}: {self.name} ({chapter_count} {chapters_text})"

    @property
    def name(self) -> str:
        """Return part name, or 'Part X' if not set."""
        return self._name or f"Part {self.number}"

    @name.setter
    def name(self, value: Optional[str]) -> None:
        """Set part name (can be None to use default)."""
        self._name = value


@dataclass
class Document:
    """Complete document structure parsed from an input file.

    A document has EITHER a list of chapters (flat) OR a list of parts
    (hierarchical). Having both or neither is invalid.

    Attributes:
        title: Document title.
        root: Base directory for resolving relative file paths. If None,
            file paths are used as-is (absolute paths recommended).
        chapters: List of chapters (flat structure, empty if using parts).
        parts: List of parts (hierarchical structure, empty if using chapters).
        default_extension: Optional default extension for files (e.g., ".txt").
        author: Optional author name.
        year: Optional publication year.
        language: Optional language code (e.g., "en").
        metadata: Dictionary of any other key-value pairs from the input file.
        id: Optional id (defaults to random 5 digit integer string)
    """

    title: str
    chapters: list[Chapter]
    parts: list[Part]

    # Common optional fields
    root: Optional[Path] = None
    default_extension: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    language: Optional[str] = None

    # Catch-all for unknown keys
    metadata: dict[str, Any] = field(default_factory=dict)

    # specific to the structure
    id: Optional[str] = field(default_factory=lambda: random_digit_string(5))

    def __post_init__(self) -> None:
        """Validate that exactly one of chapters or parts is non-empty."""
        has_chapters = bool(self.chapters)
        has_parts = bool(self.parts)

        if has_chapters and has_parts:
            raise ValueError("Document cannot have both 'chapters' and 'parts'")
        if not has_chapters and not has_parts:
            raise ValueError("Document must have either 'chapters' or 'parts'")

    def __str__(self) -> str:
        """User-friendly string representation."""
        lines = [f"Title: {self.title}"]

        if self.author:
            lines.append(f"Author: {self.author}")
        if self.year:
            lines.append(f"Year: {self.year}")
        if self.language:
            lines.append(f"Language: {self.language}")

        lines.append(f"Root: {self.root}")

        if self.default_extension:
            lines.append(f"Default extension: {self.default_extension}")

        if self.chapters:
            lines.append(f"\nChapters ({len(self.chapters)}):")
            for ch in self.chapters:
                lines.append(f"  {ch}")
        elif self.parts:
            lines.append(f"\nParts ({len(self.parts)}):")
            for part in self.parts:
                lines.append(f"  {part}")
                # Indent chapters under each part
                for ch in part.chapters:
                    lines.append(f"    {ch}")

        if self.metadata:
            lines.append(f"\nMetadata: {self.metadata}")

        return "\n".join(lines)

    @property
    def files(self) -> list[Path]:
        """Return all resolved file paths as a flat list."""
        paths = []
        for chapter in self.chapters:
            for file_ref in chapter.files:
                paths.append(file_ref.path)
        for part in self.parts:
            for chapter in part.chapters:
                for file_ref in chapter.files:
                    paths.append(file_ref.path)
        return paths

    @classmethod
    def from_json(cls, filepath: Path) -> "Document":
        """Parse a JSON input file into a Document instance.

        Args:
            filepath: Path to the JSON input file.

        Returns:
            Document instance populated with the file's contents.

        Raises:
            FileNotFoundError: If filepath doesn't exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            ValueError: If the JSON structure is invalid.
        """

        # Helper for auto-numbering
        def auto_number(items: list[dict], key: str) -> list[dict]:
            """Add missing numbers to a list of dicts based on order."""
            current = 1
            for item in items:
                if key in item:
                    current = item[key] + 1
                else:
                    item[key] = current
                    current += 1
            return items

        # Helper for parsing chapters (shared logic)
        def parse_chapters(
            chapters_data: list[dict], base: Path, default_ext: Optional[str]
        ) -> list[Chapter]:
            """Parse a list of chapter dicts into Chapter objects."""
            chapters_data = auto_number(chapters_data, "number")
            chapters = []
            for ch_data in chapters_data:
                ch_number = ch_data["number"]
                ch_name = ch_data.get("name")
                files_data = ch_data.get("files", [])

                if not files_data:
                    raise ValueError(f"Chapter {ch_number} must have at least one file")

                files = []

                for file_entry in files_data:
                    # Handle both string and dict formats
                    if isinstance(file_entry, str):
                        # string case: i.e. file in JSON defined as "./a/b.txt"
                        raw_path = file_entry
                        name = None
                    else:
                        # dict case: i.e. file in JSON defined as {"path": "./a/b.txt", "name": "shortname"}
                        raw_path = file_entry["path"]
                        name = file_entry.get("name")

                    file_path = Path(raw_path)
                    if file_path.is_absolute():
                        path = file_path
                    else:
                        path = base / file_path

                    file_ref = FileRef(path=path, name=name)

                    if default_extension and not path.suffix:
                        path = path.with_suffix(default_extension)
                        # Recreate FileRef with updated path (preserve name if present)
                        file_ref = FileRef(path=path, name=file_ref.name)

                    files.append(file_ref)

                chapter = Chapter(number=ch_number, files=files)
                if ch_name is not None:
                    chapter.name = ch_name
                chapters.append(chapter)

            return chapters

        # read JSON file
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Define fallback for root path resolution
        resolve_roots_relative_to = filepath.parent

        # Pop required and optional fields from JSON
        title = data.pop("title", "Untitled")
        raw_doc_root = data.pop("root", None)
        # Resolve base for chapter resolution (always a Path)
        doc_base = resolve_base(raw_doc_root, resolve_roots_relative_to)
        # Root to store on Document (None if not provided, otherwise resolved Path)
        doc_root = doc_base if raw_doc_root is not None else None

        default_extension = data.pop("default_extension", None)
        author = data.pop("author", None)
        year = data.pop("year", None)
        language = data.pop("language", None)

        # Pop structure data
        chapters_data = data.pop("chapters", [])
        parts_data = data.pop("parts", [])

        # Validate exactly one structure is present
        if chapters_data and parts_data:
            raise ValueError("Document cannot have both 'chapters' and 'parts'")
        if not chapters_data and not parts_data:
            raise ValueError("Document must have either 'chapters' or 'parts'")

        metadata = data  # remaining keys become metadata

        if chapters_data:
            # Parse flat structure
            chapters = parse_chapters(chapters_data, doc_base, default_extension)
            doc = cls(
                title=title,
                root=doc_root,
                chapters=chapters,
                parts=[],
                default_extension=default_extension,
                author=author,
                year=year,
                language=language,
                metadata=metadata,
            )
        elif parts_data:
            # Parse hierarchical structure
            parts_data = auto_number(parts_data, "number")
            parts = []

            for part_data in parts_data:
                part_number = part_data["number"]
                part_name = part_data.get("name")
                part_chapters_data = part_data.get("chapters", [])
                raw_part_root = part_data.get("root", None)

                if not part_chapters_data:
                    raise ValueError(
                        f"Part {part_number} must have at least one chapter"
                    )

                # Resolve base for this part's chapters
                part_base = resolve_base(
                    raw_part_root, resolve_roots_relative_to, parent_base=doc_base
                )
                part_root = part_base if raw_part_root is not None else None

                part_chapters = parse_chapters(
                    part_chapters_data, part_base, default_extension
                )
                part = Part(number=part_number, chapters=part_chapters, root=part_root)
                if part_name is not None:
                    part.name = part_name
                parts.append(part)

            doc = cls(
                title=title,
                root=doc_root,
                chapters=[],
                parts=parts,
                default_extension=default_extension,
                author=author,
                year=year,
                language=language,
                metadata=metadata,
            )

        # link parents to all Chapter, Part, FileRef in Document
        doc._link_parents()

        return doc

    def _link_parents(self) -> None:
        """Set parent references on all child objects."""
        # Hierarchical structure (parts)
        for part in self.parts:
            part.parent = self
            for chapter in part.chapters:
                chapter.parent = part
                for file_ref in chapter.files:
                    file_ref.parent = chapter

        # Flat structure (chapters only)
        for chapter in self.chapters:
            chapter.parent = self
            for file_ref in chapter.files:
                file_ref.parent = chapter

    def serialize(self) -> None:
        """Serialize this Document instance to a JSON string."""

        def convert(obj: Any) -> Any:
            if isinstance(obj, Path):
                return str(obj)
            elif isinstance(obj, Part):
                result = {
                    "number": obj.number,
                    "chapters": [convert(ch) for ch in obj.chapters],
                }
                if obj._name is not None:
                    result["name"] = obj._name
                if obj.root is not None:
                    result["root"] = str(obj.root)
                return result
            elif isinstance(obj, Chapter):
                result = {
                    "number": obj.number,
                    "files": [convert(f) for f in obj.files],
                }
                if obj._name is not None:
                    result["name"] = obj._name
                return result
            elif isinstance(obj, FileRef):
                result = {"path": str(obj.path)}
                if obj.name:
                    result["name"] = obj.name
                return result
            elif isinstance(obj, Document):
                result = {
                    "title": obj.title,
                    "root": str(obj.root),
                }
                if obj.chapters:
                    result["chapters"] = convert(obj.chapters)
                if obj.parts:
                    result["parts"] = convert(obj.parts)
                if obj.default_extension:
                    result["default_extension"] = obj.default_extension
                if obj.author:
                    result["author"] = obj.author
                if obj.year:
                    result["year"] = obj.year
                if obj.language:
                    result["language"] = obj.language
                # Merge metadata
                result.update(obj.metadata)
                return result
            elif isinstance(obj, list):
                return [convert(item) for item in obj]
            return obj

        data = convert(self)

        return json.dumps(data, indent=2)

    def to_json(self, filepath: Path, force: bool = False) -> None:
        """Serialize this Document instance to a JSON file.

        Args:
            filepath: Destination path for the JSON file.
            force: Overwrite if destination path exists.
        """
        if filepath.exists() and not force:
            raise FileExistsError(
                f"File to serialize JSON to exists (supply 'force' arg): {filepath}"
            )
        # convert this Document to a JSON string
        json_string = self.serialize()
        # create parent dirs
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json_string)

    def __repr__(self) -> str:
        """Compact representation for debugging."""
        structure = (
            f"chapters={len(self.chapters)}"
            if self.chapters
            else f"parts={len(self.parts)}"
        )
        return f"Document(title='{self.title}', {structure}, metadata_keys={list(self.metadata.keys())})"
