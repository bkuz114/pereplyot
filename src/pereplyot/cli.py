#!/usr/bin/env python3
"""
pereplyot: Unified document site generator. Takes list of documents from a
JSON input file and creates offline, static HTML allowing you to navigate easily between
the documents.

Usage:
    pereplyot INPUT [--output DIR] [--template FILE] [--force] [--strict]
               [--quiet] [--clean] [--mode MODE]

Examples:
    # outputs to dist/binder.html
    pereplyot examples/fishing_book.json

Note:
    inputfiles are style defined by:
    https://github.com/bkuz114/inputfile-parser
    (which is vendored into this project at vendor/inputfile.py; imported below)

For more information, see README.md and CHANGELOG.md.
"""

import os
import sys
import argparse
import re
import random
from docx import Document as Docx
import json
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
import yaml
import markdown
from bs4 import BeautifulSoup
import logging

# Allow direct execution from source during development (e.g., `python cli.py`)
# by adding the `src/` directory to Python's import path. This block only runs
# when the script is executed directly, not when imported as a module or run
# from a pip installation.
if __name__ == "__main__":
    # get src dir to add to python path
    src_dir = Path(__file__).resolve().parent.parent  # resolve() to handle symlinks
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

# vendored packages
from pereplyot.vendor.template_utils import render_template
from pereplyot.vendor import inputfile
from pereplyot.vendor.inputfile import Document, Chapter, Part, FileRef
from pereplyot.vendor import beautiful_soup_utils

# version string to use for --version option (comes from __init__.py)
from pereplyot import __version__

# set up template and assets defaults within the pip project
import pereplyot

# Get the package root directory using __file__.
#
# Why not importlib.resources?
#   On Windows, importlib.resources returns a MultiplexedPath object that
#   cannot be converted to a real Path without ugly string hacks. The
#   __file__ approach is simpler and works reliably because setuptools
#   guarantees that package data (templates, assets) are installed to the
#   filesystem alongside the package.
#
# Assumption:
#   This assumes the package is installed to a filesystem directory
#   (not a zip file). For a CLI tool distributed via PyPI, this is true
#   for all normal installation methods (pip, pipx, etc.).
#
# Package structure expected:
#   pereplyot/
#   ├── __init__.py
#   ├── cli.py
#   ├── templates/
#   │   └── default_template.html
#   └── assets/
#       ├── css/
#       └── js/
PACKAGE_ROOT = Path(pereplyot.__file__).parent

# Verify the directory exists (helpful error if structure changes)
if not PACKAGE_ROOT.exists():
    raise RuntimeError(f"Package root not found at {PACKAGE_ROOT}")

# Default paths relative to package root
DEFAULT_TEMPLATE = PACKAGE_ROOT / "templates" / "default_template.html"
DEFAULT_ASSETS = PACKAGE_ROOT / "assets"

# ============================================================================
# CONFIGURATION
# ============================================================================

# Maximum heading depth for TOC (1=h1, 2=h2, 3=h3, 4=h4)
TOC_MAX_DEPTH = 4

# Markdown extensions
MD_EXTENSIONS = [
    "tables",
    "fenced_code",
    "codehilite",
    "smarty",
]

# document mode mapping
MODE_MAPPING = {"auto": 0, "wiki": 1, "github": 2}

# ============================================================================
# LOGGING
# ============================================================================


# Setup basic logging (called once in main)
def setup_logging(quiet: bool = False):
    """Configure logging based on quiet flag."""
    level = logging.ERROR if quiet else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",  # Just the message, no extra prefix
        stream=sys.stdout,
    )


# Get module logger
logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def read_file(filepath: Path) -> str:
    """
    Reads and validates file and returns raw content.

    Args:
        filepath: Path to file.

    Returns:
        Raw text of file.

    Raises:
        FileNotFoundError: If filepath doesn't exist.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Input file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def random_digit_string(x: int) -> str:
    """
    Generate a string of random digits of length x.

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


# ============================================================================
# MARKDOWN + YAML FRONTMATTER PROCESSING
# ============================================================================


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter from markdown content and return both.

    Args:
        content: string content of an .md file (including YAML frontmatter)

    Returns:
        (metadata_dict, remaining_markdown_string)

    Frontmatter format:
        ---
        title: My Document
        description: Something useful
        ---
        # Rest of markdown...

    Graceful degradation:
        - No frontmatter → ({}, content)
        - No closing '---' → ({}, content)
        - Malformed YAML → ({}, content) with warning
    """
    lines = content.split("\n")

    # Check for opening --- (must be first line)
    if not lines or lines[0].strip() != "---":
        return {}, content

    # Find closing ---
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        # No closing delimiter — treat as no frontmatter
        return {}, content

    # Extract YAML block and remaining content
    yaml_block = "\n".join(lines[1:end_idx])
    rest_content = "\n".join(lines[end_idx + 1 :])

    # Parse YAML
    try:
        metadata = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError as e:
        logger.warning(f"⚠️  Warning: Malformed frontmatter YAML: {e}")
        logger.warning("   Ignoring frontmatter and continuing.")
        return {}, content

    return metadata, rest_content


# ============================================================================
# TOC GENERATION
# ============================================================================


def render_toc(toc_entries: List[Dict], mode: int, current_depth: int = 1) -> str:
    """
    Render TOC entries as nested HTML list based on document mode.

    Args:
        toc_entries: List of dicts with 'level', 'text', 'id' keys
            - 'level': corresponds to css class for indenting
            - 'text': text to dispaly for that entry
            - 'id': tag id it maps to
        mode: int indicating document type. Options: 1 (github style), 2 (wiki style)
            - Github mode: First h1 gets up-arrow anchored to #top in TOC
            - Wiki mode: All h1s as normal headings. Back to top link before all
        current_depth: Starting depth (default 1, for h1)

    Returns:
        HTML string of nested <ul> and <li> elements

    Note:
        This function uses recursion to handle nested heading levels.
        h1 is rendered as a special "Back to top" link.
    """

    # Filter to only include entries at or below max depth
    entries = [e for e in toc_entries if e["level"] <= TOC_MAX_DEPTH]

    html = '<ul class="toc-list">\n'

    # counter to offset which css styling class to use for heading entries
    # (wiki docs should use toc-level-h2 for h1, toc-level-h3 for h2, etc.)
    offset = 0

    # wiki mode: create anchor to top of document
    if mode == 1:
        html += (
            f'  <li><a href="#start" class="toc-level-h1 top-link">↑ Start</a></li>\n'
        )
        offset = 1

    # create <li> for each heading
    for entry in entries:
        level = entry["level"]
        text = entry["text"]
        anchor_id = entry["id"]
        level_class = f"toc-level-h{level + offset}"

        if level == 1 and mode == 2 and entry == entries[0]:
            # First h1 in document mode: up-arrow
            # Back to top link (uses #top anchor from <html id="top">)
            html += f'  <li><a href="#top" class="toc-level-h1 top-link">↑ {text}</a></li>\n'
        else:
            # Wiki mode or non-first h1 in document mode (shouldn't happen)
            html += f'  <li><a href="#{anchor_id}" class="{level_class} chap-link">{text}</a></li>\n'

    html += "</ul>\n"
    return html


def create_toc_entries(doc: Document, max_depth: int = 4) -> List[Dict]:
    """
    Build TOC entries for the document

    Args:
        doc: Document object generated from inputfile JSON
        max_depth: Maximum heading level to include (1-4).

    Returns:
        toc_entries: a list of dicts with keys: level, text, id.
    """
    toc_entries = []
    # Create an h3 header for each chapter
    # (revise later -- for now the styling works when only 1 depth)
    for chapter in doc.chapters:
        # get id attr that was added in
        id_attr = chapter.id_attr
        toc_entries.append(
            {
                "level": 2,
                "text": chapter.name,
                "id": id_attr,
            }
        )
    return toc_entries


def create_toc(doc: Document) -> str:
    toc_entries = create_toc_entries(doc, TOC_MAX_DEPTH)
    return render_toc(toc_entries, 1)


# ============================================================================
# DOCUMENT GENERATION
# ============================================================================


def template_html(
    template_path: Path,
    content: str,
    frontmatter: Dict[str, str],
    toc_html: str,
    asset_path_prefix: str,
) -> str:
    """
    Embed converted markdown content into template file.

    Args:
        template_path: Path to the template .html file.
        content: string of content to embed at {{content}} placeholder
        frontmatter: dictionary of the key/value pairs extracted from YAML frontmatter.
            Used to embed data to dcoument placeholders. Example:
            frontmatter = {"key1": "value1", "key2": "value2"},
            "value1" will be embedded at {{key1}} placeholder, "value2" at {{key2}}, etc.
        toc: string of content to embed at {{toc}} placeholder

    Returns:
        Content of template file with embedded markdown content and title.

    Raises:
        FileNotFoundError: If template_path doesn't exist.
        ValueError: If template_path isn't .html file
    """

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    if not template_path.suffix == ".html":
        raise ValueError(
            f"Template file expected .html file, got {template_path.suffix}: {template_path}"
        )

    # Read template file
    template_content = template_path.read_text(encoding="utf-8")

    # Build substitutions
    substitutions = {
        "content": content,
        "toc": toc_html,
        "asset_path_prefix": asset_path_prefix,
    }

    # merge frontmatter data
    substitutions |= frontmatter

    # Generate warning comment referencing the source template
    warning_msg = f"THIS FILE IS GENERATED. DO NOT EDIT DIRECTLY."

    # Inject content into HTML template
    full_content = render_template(
        template_content,
        substitutions,
        strict=True,
        warning_comment=warning_msg,
    )

    return full_content


def write_html_file(content: str, output: Path, force: bool) -> None:
    """
    Write the final HTML file, checking for existing file and --force flag.

    Args:
        content: Final HTML string.
        output: Path to write html file to
        force: Whether to overwrite existing file.

    Raises:
        FileExistsError: If file exists and force is False.
    """
    if output.exists() and not force:
        raise FileExistsError(f"{output} already exists. Use --force to overwrite.")

    output.parent.mkdir(parents=True, exist_ok=True)

    # convert to BeautifulSoup and prettify
    soup = BeautifulSoup(content, "html.parser")
    beautiful_soup_utils.write_soup_to_file(
        soup, output, True, True, True, [], [], False
    )
    logger.info(f"✅ Generated: {output}")


def create_home(doc: Document) -> str:
    """Creates HTML for initial page load splash screen.

    Args:
        doc: Document object generated from inputfile JSON.

    Returns:
        HTML string for the home page with centered layout and metadata display.
    """
    metadata = doc.metadata
    title = getattr(doc, "title", "Untitled Document")

    # Handle author(s) - could be string or list
    author = doc.author or metadata.get("authors")
    if isinstance(author, list):
        author = ", ".join(author)

    date = doc.year or metadata.get("date") or metadata.get("last_modified")
    description = metadata.get("description") or metadata.get("abstract")
    version = metadata.get("version") or metadata.get("edition")
    tags = metadata.get("tags") or metadata.get("keywords")
    if isinstance(tags, list):
        tags = ", ".join(tags)

    # Build metadata rows conditionally
    metadata_rows = []

    if author:
        metadata_rows.append(f"""
            <div class="splash-metadata-row">
                <span class="splash-metadata-label">Author</span>
                <span class="splash-metadata-value">{author}</span>
            </div>
        """)

    if date:
        metadata_rows.append(f"""
            <div class="splash-metadata-row">
                <span class="splash-metadata-label">Date</span>
                <span class="splash-metadata-value">{date}</span>
            </div>
        """)

    if version:
        metadata_rows.append(f"""
            <div class="splash-metadata-row">
                <span class="splash-metadata-label">Version</span>
                <span class="splash-metadata-value">{version}</span>
            </div>
        """)

    if tags:
        metadata_rows.append(f"""
            <div class="splash-metadata-row">
                <span class="splash-metadata-label">Tags</span>
                <span class="splash-metadata-value">{tags}</span>
            </div>
        """)

    metadata_html = "".join(metadata_rows) if metadata_rows else ""

    description_html = (
        f"""
        <div class="splash-description">
            {description}
        </div>
    """
        if description
        else ""
    )

    return f"""
    <div class="splash-container">
        <div class="splash-card">
            <h1 class="splash-title">{title}</h1>

            {metadata_html}

            {description_html}

            <div class="splash-footer">
                <p class="splash-instruction">
                    ← Select a section from the table of contents to begin
                </p>
            </div>
        </div>
    </div>
    """


def convert_markdown_to_html(filepath: str, mode: int) -> str:
    """
    Convert Markdown file to HTML using python-markdown.

    Args:
        filepath: Path to a .md file
        mode: int indicating document type. Options: 1 (github style), 2 (wiki style)
            - Github mode: First h1 gets up-arrow anchored to #top in TOC
            - Wiki mode: All h1s as normal headings in TOC.

    Returns: HTML string with heading IDs added
    """
    if not filepath.exists():
        raise Exception(f".md file {filepath} does not exist!")
    if not filepath.suffix == ".md":
        raise Exception(f"File is not .md! {filepath}")

    # extract content
    raw_content = read_file(filepath)

    # remove YAML frontmatter
    metadata, md_content = parse_frontmatter(raw_content)

    # Convert markdown to HTML
    raw_html = markdown.markdown(md_content, extensions=MD_EXTENSIONS)

    return raw_html


def convert_txt_to_html(filepath: Path) -> str:
    """
    Convert .txt file to HTML

    Args:
        filepath: Path to .txt file

    Returns:
        HTML string
    """
    if not filepath.exists():
        raise Exception(f".txt file {filepath} does not exist!")
    if not filepath.suffix == ".txt":
        raise Exception(f"File is not .txt! {filepath}")
    return read_file(filepath)


def convert_docx_to_html(filepath: Path) -> str:
    """
    Convert .docx file to HTML

    Args:
        filepath: Path to .docx file

    Returns:
        HTML string
    """
    if not filepath.exists():
        raise Exception(f".docx file {filepath} does not exist!")
    if not filepath.suffix == ".docx":
        raise Exception(f"File is not .docx! {filepath}")
    # must loop through all paragraphs to get all text
    doc = Docx(filepath)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    raw_content = "\n".join(full_text)
    return raw_content


def post_process_file_html(html: str) -> str:
    return f'<p class="file-section">{html}</p>'


def post_process_chapter_html(html: str, title: str) -> tuple[str, str]:
    """Wrap chapter HTML in a div and generate a unique identifier for it

    Args:
        html: HTML string of the chapter's content (made up of all its files)
        title: string chapter of title

    Returns:
        tuple of (CONTENT, ID), where CONTENT: wrapper HTML string, and
        id is a string, a unique id for this content.
        *NOTE*: this id is NOT for an id attr, will be used by js + TOC to
        load content. SPecifically: ID / CONTENT will be added as key/value
        pair to dict that gets written to js file sections.js, and added as
        href attr for TOC link for this content; when user clicks on that
        link, scripts.js will dynamically retrieve this content from
        sections.js object and load
    """
    id_attr = random_digit_string(5)
    return (
        f'<div class="chapter-section"><h2 class="chapter-title">{title}</h2>{html}</div>',
        id_attr,
    )


# ============================================================================
# HANDLING OF ASSETS AND OTHER ARTIFACTS
# ============================================================================


def copy_assets_to_output(
    assets_path: Path, assets_dest_dir: Path, force: bool = False
) -> Path:
    """
    Copy the assets directory to the output file's parent directory.

    This function copies the entire assets directory (including all contents)
    to the same directory where the output file will live. This ensures that
    relative asset references (e.g., `assets/css/styles.css`) resolve correctly
    when the output file is opened in a browser.

    Args:
        assets_path: Path to the source assets directory.
        assets_dest_dir: Path to the copy assets to.
        force: If True, overwrite existing assets directory; if False, raise
               error if destination already exists.

    Returns: None

    Raises:
        FileNotFoundError: If assets_path does not exist.
        NotADirectoryError: If assets_path is not a directory.
        FileExistsError: If assets_dest_dir exists and force is False.
        OSError: For other file operation errors (permissions, disk full, etc.).

    Examples:
        >>> from pathlib import Path
        >>> assets = Path("/project/assets")
        >>> output = Path("/project/output/assets")
        >>> copy_assets_to_output(assets, output, force=True)
        # Copies /project/assets to /project/output/assets

    Notes:
        - Uses shutil.copytree for recursive directory copy.
        - The destination directory name matches the source directory name.
        - Existing symlinks are preserved (follow_symlinks=False).
        - If force=True, any existing destination is removed before copying.
    """
    # Validate source
    if not assets_path.exists():
        raise FileNotFoundError(f"Assets path does not exist: {assets_path}")

    if not assets_path.is_dir():
        raise NotADirectoryError(f"Assets path is not a directory: {assets_path}")

    # Handle existing destination
    if assets_dest_dir.exists():
        if force:
            shutil.rmtree(assets_dest_dir)  # Remove entire existing directory
        else:
            raise FileExistsError(
                f"Destination already exists: {assets_dest_dir}\n"
                f"Use force=True to overwrite."
            )

    # Copy the directory
    try:
        shutil.copytree(
            assets_path,
            assets_dest_dir,
            symlinks=False,  # Copy symlinks as links (not dereferenced)
            ignore_dangling_symlinks=True,
            dirs_exist_ok=False,  # Should not happen due to check above
        )
    except OSError as e:
        raise OSError(
            f"Failed to copy assets from {assets_path} to {assets_dest_dir}: {e}"
        )


def get_asset_path_prefix(html_path: Path, assets_dir: Path) -> str:
    """
    Calculate the relative filesystem path from an HTML file to an assets directory.

    This function is designed for static site generation where you need to insert
    asset paths (CSS, JS, images) into HTML files using relative URLs. For example,
    if your HTML file lives in a nested directory structure, this tells you how
    many "../" segments are needed to reach the assets directory from that HTML
    file's location.

    The returned path always uses POSIX-style forward slashes ("/") and includes
    a trailing slash for easy concatenation with filenames.

    Examples:
        >>> from pathlib import Path
        >>> html_path = Path("dist/getting-started/install.html")
        >>> assets_dir = Path("dist/assets/")
        >>> get_asset_path_prefix(html_path, assets_dir)
        '../assets/'

        >>> html_path = Path("dist/install.html")
        >>> assets_dir = Path("dist/assets/")
        >>> get_asset_path_prefix(html_path, assets_dir)
        'assets/'

        >>> html_path = Path("dist/index.html")
        >>> assets_dir = Path("dist/assets/")
        >>> get_asset_path_prefix(html_path, assets_dir)
        'assets/'

    Args:
        html_path: Path to the HTML file (may not exist on disk yet)
        assets_dir: Path to the directory containing assets (may not exist yet)

    Returns:
        A relative path string ending with "/". Returns empty string if the
        HTML file and assets directory are in the same directory.

    Notes:
        This function works with hypothetical paths that don't exist on disk.
        It performs purely lexical path manipulation without filesystem access.

    Why not use Path.relative_to()?
        Path.relative_to() only works when one path is a direct subpath of the
        other. In our typical use case, the HTML file is nested (e.g.,
        "docs/guide/install.html") while the assets directory is elsewhere
        (e.g., "assets/"). These are cousin paths, not parent-child, so
        relative_to() raises ValueError. We need to ascend using "../" segments,
        which os.path.relpath handles.
    """

    # Get the directory containing the HTML file
    html_dir = html_path.parent

    # Compute rel path from HTML dir to assets dir
    # - os.path.relpath() computes rel path from start to target
    #   e.g.: relpath("dist/getting-started", "dist/assets") -> "../assets"
    # - counts ".." segments automatically, even for deeply nested paths.
    # - returns OS-native separators
    rel_path = os.path.relpath(str(assets_dir), start=str(html_dir))

    # os.path.relpath returns . if both dirs same
    if rel_path == ".":
        return ""

    # Convert Windows backslashes to forward slashes for HTML compatibility
    return rel_path.replace("\\", "/") + "/"


def write_javascript_helper(html_data: Dict[str, str], filepath: Path) -> None:
    """
    Write a JavaScript helper file that maps section IDs to HTML content.

    The generated file creates a global object `SECTION_CONTENT` where each key
    corresponds to a section identifier and each value is the HTML string for
    that section. This enables client-side section swapping without multiple
    hidden divs, allowing smooth fade transitions.

    Args:
        html_data: Dictionary mapping section IDs to HTML content strings.
            Example:
                {
                    "1234": "<div class='chapter-section'>Section 1 content</div>",
                    "1652": "<div class='chapter-section'>Section 2 content</div>",
                }
        filepath: Destination path for the generated JavaScript file. Parent
            directories will be created if they do not exist.

    Returns:
        None

    Raises:
        OSError: If the file cannot be written due to permissions or disk space.

    Note:
        The generated file should be included in the HTML before any script
        that references `SECTION_CONTENT`.

    Example:
        >>> write_javascript_helper({"home": "<div>Home</div>"}, Path("assets/sections.js"))
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Serialize the dictionary to a compact JSON string
    # Using ensure_ascii=False preserves Unicode characters in content
    content_json = json.dumps(html_data, ensure_ascii=False)

    # Write the JavaScript file with the global object declaration
    js_content = f"""// Auto-generated by write_javascript_helper()
// Do not edit directly. Regenerate from source data.

const SECTION_CONTENT = {content_json};
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(js_content)


# ============================================================================
# MAIN DRIVER
# ============================================================================


def process_files(doc: Document, mode, strict: bool) -> Dict[str, str]:
    """
    Iterates through each file in the JSON document, gets raw content,
    converts it to an HTML string, and returns a dictionary of that content
    (mapped to unique keys)

    The HTML strings generated will NOT get embedded into final HTML file;
    the dictionary returned by this function instead gets written to a javscript
    file, and javscript dynamically loads the content when user clicks TOC links

    Args:
        doc: Document object generated from input JSON file.
        strict: If True, abort on first error and re-raise the exception.
            If False, log errors and continue processing remaining files.
        mode: int indicating document type. Options: 1 (github style), 2 (wiki style)
            - Github mode: First h1 gets up-arrow anchored to #top in TOC;
              doc title extracted from first h1 if not in frontmatter.
            - Wiki mode: All h1s as normal headings in TOC; doc title
              based on filename if not in frontmatter.

    Returns:
        a dictionary of {unique_ID : HTML_content} pairs (one for each "chapter"), where:
        - unique_ID: an id generated for the constructed chapter
        - HTML_content: HTML string of all data for a chapter (chapters
          can have multiple files)
    """

    html = {}
    failed_count = 0
    for i, chapter in enumerate(doc.chapters):
        chapter_html = ""
        for j, fileRef in enumerate(chapter.files):
            try:
                # HTML for this file
                file_html = ""
                filepath = fileRef.path
                file_ext = filepath.suffix.lower()
                if file_ext == ".txt":
                    file_html = convert_txt_to_html(filepath)
                elif file_ext == ".docx":
                    file_html = convert_docx_to_html(filepath)
                elif file_ext == ".markdown":
                    file_html = convert_markdown_to_html(filepath, mode)
                file_html = post_process_file_html(file_html)

                # add <hr> if multiple files
                if j > 0:
                    chapter_html += "<hr>"
                chapter_html += file_html

            except Exception as e:
                logger.error(f"   ❌ Failed: {fileRef.path} - {e}")
                failed_count += 1
                if strict:
                    raise  # Fail fast in strict mode
        # post-process (Add title, etc)
        chapter_name = f"Chapter: {chapter.name}"
        # wrap in div and get the id attr assigned to it
        chapter_html, id_attr = post_process_chapter_html(chapter_html, chapter_name)
        # modify the Chapter object to have the id attr
        chapter.id_attr = id_attr
        # add to main content html
        html[id_attr] = chapter_html

    logger.info(
        f"\n✅ Processed {len(doc.files) - failed_count} of {len(doc.files)} files"
    )
    if failed_count > 0 and not strict:
        logger.error(f"   ⚠️  {failed_count} file(s) failed")

    return html


def generate_binder(
    doc: Document,
    output_file: Path,
    template_path: Path,
    assets_path: Path,
    final_assets_dir: Path,
    js_helper_path: Path,
    force: bool,
    strict: bool,
    mode: int,
) -> None:
    """
    Creates HTML site from list of files in JSON inputfile.

    Args:
        doc: Document object generated from input JSON file.
        output_file: Path to the output file to write
        template_path: Path to the HTML template file
        assets_path: Path to the source assets directory (css/, js/).
        final_assets_dir: Path where assets will be copied in the output
            directory (e.g., dist/assets/).
        force: If True, overwrite existing output files. If False, raise
            FileExistsError when output already exists.
        strict: If True, abort on first error and re-raise the exception.
            If False, log errors and continue processing remaining files.
        mode: int indicating document type. Options: 1 (github style), 2 (wiki style)
            - Github mode: First h1 gets up-arrow anchored to #top in TOC;
              doc title extracted from first h1 if not in frontmatter.
            - Wiki mode: All h1s as normal headings in TOC; doc title
              based on filename if not in frontmatter.

    Returns:
        None
    """

    # Document title for HTML <title> and other branding
    title = doc.title

    # Document description for HTML metadata
    description = getattr(doc, "description", "")

    # metadata to embed in HTML (keys are placeholders in template file;
    # will embed their values in the placeholder)
    metadata = {"title": title, "description": description}

    # Calculate asset path prefix
    asset_path_prefix = get_asset_path_prefix(output_file, final_assets_dir)

    # Convert files specified in JSON input file into HTML strings
    #
    # - process_files saves the HTML strings in a dict.
    # - keys are unique ids; those ids will become href attrs in <a> of the TOC,
    #   indicating which content to open (in create_toc)
    # - dict will be written to a js file (write_javascript_helper)
    #   when user clicks a TOC <a>, js gets the href attr, then uses the
    #   helper file to get the HTML content and dynamically load it.
    #
    # Note: process_files modifies doc to add the id for created chapter div
    # to each Chapter obj, which is how TOC gets constructed.
    content_dict = process_files(doc, mode, strict)

    # create TOC
    toc = create_toc(doc)

    # create splash page to load on page load
    splash_html = create_home(doc)

    # add splash page HTML to content dict
    # (don't change "start"! scripts.js depends on it)
    content_dict["start"] = splash_html

    # Render template
    final_html = template_html(
        template_path,
        splash_html,
        metadata,
        toc,
        asset_path_prefix,
    )

    # Write output
    write_html_file(final_html, output_file, force)

    # Copy assets once after all files processed (or before, doesn't matter)
    copy_assets_to_output(assets_path, final_assets_dir, force)

    # Write js helper file (do after copying assets in case it lives there)
    write_javascript_helper(content_dict, js_helper_path)


# ============================================================================
# MAIN
# ============================================================================


def main():

    # help string to add to path arguments
    path_help = (
        "Relative paths are resolved relative to the current working directory "
        "(not necessarily this script's dir)."
    )

    parser = argparse.ArgumentParser(
        description="Generate an offline HTML page for navigating a binder of documents (.txt, .md, or .docx)",
        epilog="Example: pereplyot example/fishing_doc.json --force",
    )
    parser.add_argument(
        "input",
        type=Path,
        help=f"Path to the JSON manifest file (e.g., input.json). {path_help}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=False,
        default="dist",
        help=f"Path to output dir (e.g., dist). {path_help}",
    )
    parser.add_argument(
        "--assets",
        type=Path,
        required=False,
        default=DEFAULT_ASSETS,
        help=f"Path to assets directory (e.g., assets). {path_help}",
    )
    parser.add_argument(
        "--template",
        type=Path,
        required=False,
        default=DEFAULT_TEMPLATE,
        help=f"Path to template file (e.g., templates/default_template.html). {path_help}",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file if it exists",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete output directory before processing (requires --force)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on first failure",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["auto", "github", "wiki"],
        default="auto",
        help="Document mode: auto (detect), github (single h1 -- doc title), wiki (multiple h1s)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all non-error output (useful for scripting)",
    )
    parser.add_argument("--version", "-v", action="version", version=f"{__version__}")
    args = parser.parse_args()

    # Setup logging before any script logic
    setup_logging(quiet=args.quiet)

    # Resolve all paths to absolute (handles relative, symlinks, etc.)
    # rel paths will be evaluated rel callers cwd, NOT script dir
    input_path = args.input.resolve()
    output_dir = args.output.resolve()
    template_path = args.template.resolve()
    assets_path = args.assets.resolve()

    # standardize document mode
    if not args.mode in MODE_MAPPING:
        raise ValueError(
            f"Bug: --mode passed argparse validation, but not valid via MODE_MAPPING:\n\tValid: {', '.join(list(MODE_MAPPING.keys()))}\n\tGiven: {args.mode}"
        )
    document_mode = MODE_MAPPING[args.mode]

    # delete output dir if exists and --clean provided
    if args.clean:
        if not args.force:
            logger.error("❌ Error: --clean requires --force")
            sys.exit(1)
        if output_dir.exists():
            shutil.rmtree(output_dir)
            logger.info(f"🧹 Cleaned output directory: {output_dir}")

    # parse input JSON into Document object
    input_file = args.input.resolve()  # resolve rel cwd
    doc = Document.from_json(input_file)
    title = doc.title

    # Final assets directory (shared across all files)
    final_assets_dir = output_dir / "assets"

    # Path to write helper javascript file to
    # (for switching content via TOC)
    js_helper_path = final_assets_dir / "js/sections.js"

    # Process all the files
    generate_binder(
        doc,
        output_dir / "binder.html",
        template_path,
        assets_path,
        final_assets_dir,
        js_helper_path,
        args.force,
        args.strict,
        document_mode,
    )


if __name__ == "__main__":
    main()
