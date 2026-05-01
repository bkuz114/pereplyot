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
from typing import Optional, Any

# ============================================================================
# Data structures
# ============================================================================


@dataclass(frozen=True)
class FileRef:
    """Reference to a single source file within a chapter.

    Attributes:
        path: Path to the file (Parser will resolve relative to Document.root).
        name: Optional display name (overrides the filename in reports).
    """

    path: Path
    name: Optional[str] = None

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
        _name: Optional internal name storage. Access via `name` property.
    """

    number: int
    files: list[FileRef]
    _name: Optional[str] = field(default=None, repr=False)

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
        _name: Optional internal name storage. Access via `name` property.
    """

    number: int
    chapters: list[Chapter]
    _name: Optional[str] = field(default=None, repr=False)

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
            chapters_data: list[dict], root: Path, default_ext: Optional[str]
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
                        if root:
                            # resolve relative to document root if provided
                            path = root / file_entry
                        else:
                            # treat path as is
                            path = Path(file_entry)
                        file_ref = FileRef(path=path)
                    else:
                        # dict case: i.e. file in JSON defined as {"path": "./a/b.txt", "name": "shortname"}
                        if root:
                            # resolve relative to document root if provided
                            path = root / file_entry["path"]
                        else:
                            # treat path as is
                            path = Path(file_entry["path"])
                        name = file_entry.get("name")
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

        # Pop required and optional fields from JSON
        title = data.pop("title", "Untitled")
        root = data.pop("root", None)
        # Document object will expect root to be a Path
        if root:
            root_path = Path(root)
            if root_path.is_absolute():
                # root was absolute -- keep as-is
                root = root_path
            else:
                # root was relative -- resolve rel source json file
                root = (filepath.parent / root_path).resolve()
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

        # Parse flat structure
        if chapters_data:
            chapters = parse_chapters(chapters_data, root, default_extension)
            return cls(
                title=title,
                root=root,
                chapters=chapters,
                parts=[],
                default_extension=default_extension,
                author=author,
                year=year,
                language=language,
                metadata=metadata,
            )

        # Parse hierarchical structure
        parts_data = auto_number(parts_data, "number")
        parts = []
        for part_data in parts_data:
            part_number = part_data["number"]
            part_name = part_data.get("name")
            part_chapters_data = part_data.get("chapters", [])

            if not part_chapters_data:
                raise ValueError(f"Part {part_number} must have at least one chapter")

            part_chapters = parse_chapters(part_chapters_data, root, default_extension)
            part = Part(number=part_number, chapters=part_chapters)
            if part_name is not None:
                part.name = part_name
            parts.append(part)

        return cls(
            title=title,
            root=root,
            chapters=[],
            parts=parts,
            default_extension=default_extension,
            author=author,
            year=year,
            language=language,
            metadata=metadata,
        )

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
