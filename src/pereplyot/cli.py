#!/usr/bin/env python3
"""
pereplyot: Unified document site generator. Takes list of documents from a
JSON input file and creates offline, static HTML allowing you to navigate easily between
the documents.

Usage:
    pereplyot INPUT [--output DIR] [--template FILE] [--force] [--nuclear] [--strict]
               [--quiet] [--clean] [--browser] [--home HOMEPAGE_STYLE]

Examples:
    # outputs to dist/binder.html
    pereplyot examples/fishing_book.json

Note:
    inputfiles are style defined by:
    https://github.com/bkuz114/inputfile-parser
    (which is vendored into this project at vendor/inputfile.py; imported below)

For more information, see README.md and CHANGELOG.md.
"""

from datetime import datetime as dt
import os
import sys
import argparse
import re
import random
import mammoth
import json
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
import yaml
import markdown
import webbrowser
from bs4 import BeautifulSoup
from io import StringIO
import logging
from striprtf.striprtf import rtf_to_text

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

# tags to use in TOC generation
TOC_TAGS = ["h1", "h2", "h3", "h4"]

# tags to use for js intra-page navigation (<| |> buttons)
NAV_TAGS = TOC_TAGS + ["hr"]

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
    # suppress logs from rtfparse module
    logging.getLogger("rtfparse").setLevel(logging.CRITICAL)


# Get module logger
logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def make_path_writable(function, path):
    """Make a path writable and retry the function."""
    os.chmod(path, stat.S_IWRITE)
    function(path)


def remove_path(path: Path, force: bool, nuclear: bool) -> None:
    """Remove a path, optionally handling Windows read-only attributes.

    Args:
        path: The path to remove.
        force: If False, raises FileExistsError when the path exists.
               If True, attempts normal deletion via shutil.rmtree.
        nuclear: If True, uses aggressive deletion that strips read-only
                 permissions before retrying (Windows only). Implies force.

    Raises:
        FileExistsError: If force and nuclear are both False and path exists.

    Notes:
        The nuclear option is a Windows-specific workaround for `[WinError 5] Access is denied`
        errors that occur even when the path is deletable via Explorer. It applies
        `os.chmod(path, stat.S_IWRITE)` to any item that fails deletion and retries.

        Use nuclear only as a last resort when standard --force fails with permission errors.
    """
    if not path.exists():
        return

    try:
        if nuclear:
            shutil.rmtree(path, onerror=make_path_writable)
        elif force:
            shutil.rmtree(path)
        else:
            raise FileExistsError(
                f"Path already exists: {path}\nUse --force to overwrite."
            )
    except Exception as e:
        raise RuntimeError(f"Failed to remove path. Error: {e}")


def timestamp() -> str:
    """Return a timestamp string safe for use in filenames.

    Returns:
        str: Current timestamp in format YYYY_MM_DD-HH_MM_SS.
    """
    # format the datetime without any spaces
    fmt = "%Y_%m_%d-%H_%M_%S"
    ct = dt.now().strftime(fmt)
    return str(ct)


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


def sequential_replacements(text: str, replacements: list[list[str, str]]) -> str:
    """Apply a series of substring replacements

    Each replacement replaces all occurrences of a substring before the next
    replacement is applied. This means later replacements will operate on the
    output of earlier ones, which can produce unexpected results when
    replacements are not independent (e.g., swapping values or overlapping
    patterns).

    Args:
        text: The input string to modify.
        replacements: A list of [target, replacement] pairs. Each pair must
            contain exactly two strings.

    Returns:
        The transformed string after applying all replacements in order.

    Example:
        >>> sequential_replacements("ab", [["a", "b"], ["b", "a"]])
        "aa"  # Note: not "ba" due to sequential application.
    """
    for target, replacement in replacements:
        text = text.replace(target, replacement)
    return text


# ============================================================================
# MARKDOWN + YAML FRONTMATTER PROCESSING
# ============================================================================


def determine_output(
    base_output: Path,
    title: str,
    nest: bool,
    use_title: bool,
    use_timestamp: bool,
) -> Tuple[Path, Path]:
    """
    Determines path to output dir based on user-provided flags

    Args:
        base_output: Base output dir (other dirs will nest in this if needed)
        title: Project title (used for constructing dirs and/or filenames when use_title True).
            *NOTE*: whitespace converted to _ to avoid scripting issues
        nest: (boolean) Whether --nest flag set.
            When True, per-run dirs are created.
            When False, flat files in output
        use_title: (boolean) Whether --use-title flag set.
            When True, names output dir and/or filename with title
        use_timestamp: (boolean) Whether --timestamp flag set.
            When True, timestamps dir and/or filename

    Returns: Tuple of Path to HTML file, Path to output dir

    Examples:
        # No flags (flat files in default output dir)
        /dist/index.html
        *WARNING*: collisions on repeated runs

        # --use-title (flat files + title on filename)
        /dist/proj1.html
        *WARNING*: collisions on repeated runs of same project

        # --timestamp (timestamp file)
        /dist/20260429_143052.html

        # --use-title --timestamp (title + ts on filename)
        /dist/proj1_20260429_143052.html

        # --use-title --nest (dedicated project dir)
        /dist/proj1/index.html
        *WARNING*: collisions on repeated runs of same project

        # --timestamp --nest (per run timestamp dir)
        /dist/20260429_143052/index.html

        # --use-title --timestamp --nest (dedicated project dir + nested timestamp dir)
        /dist/proj1/20260429_143052/index.html
    """
    # resolve custom output relative cwd
    base_output = base_output.resolve()
    # ensure title supplied if want to --use-title
    if use_title and not title:
        raise ValueError("No title when specifying --use-title")
    # rule out invalid combo: ~timestamp, ~use-title, nest
    if nest and not use_timestamp and not use_title:
        raise ValueError("--nest must have either --timestamp or --use-title")

    # convert whitespace to _ in title and make lower case
    title = title.replace(" ", "_").lower()

    # Output directory and filename.
    #
    # dist/index.html            //
    # dist/proj.html             // --use-title
    # dist/12345.html            // --timestamp
    # dist/proj_12345.html       // --use-title, --timestamp
    # dist/proj/index.html       // --use-title, --nest
    # dist/12345/index.html      // --timestamp, --nest
    # dist/proj/12345/index.html // --use-title, --timestamp, --nest

    default_filename = "index.html"
    ts = timestamp()

    if not use_timestamp and not use_title and not nest:
        # default no args (dist/index.html)
        output_dir = base_output
        filename = default_filename
    elif not use_timestamp and not use_title and nest:
        # not valid, doesn't make sense
        raise ValueError("--nest must have either --timestamp or --use-title")
    elif use_timestamp and not use_title and not nest:
        # timestamped file in default dir
        output_dir = base_output
        filename = f"{ts}.html"
    elif not use_timestamp and use_title and not nest:
        # name file after project , into default dir (not nested)
        output_dir = base_output
        filename = f"{title}.html"
    elif use_timestamp and use_title and not nest:
        # name file after project + ts , into default dir
        output_dir = base_output
        filename = f"{title}_{ts}.html"
    elif not use_timestamp and use_title and nest:
        # dedicated (nested) proj dir
        output_dir = base_output / title
        filename = default_filename
    elif use_timestamp and use_title and nest:
        # dedicated (nested) proj dir with timestamped dir
        output_dir = base_output / title / ts
        filename = default_filename
    elif use_timestamp and not use_title and nest:
        # dedicated (nested) timestampped dir
        output_dir = base_output / ts
        filename = default_filename

    # Final path to HTML file
    output_file = output_dir / filename

    return output_file, output_dir


# ============================================================================
# MARKDOWN + YAML FRONTMATTER PROCESSING
# ============================================================================


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter from markdown content and return both.

    Args:
        content: string content of a markdown file (including YAML frontmatter)

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


def render_toc(toc_entries: List[Dict], main_toc: bool = False) -> str:
    """
    Render TOC entries as nested HTML list

    Args:
        toc_entries: List of dicts with 'level', 'text', 'id' keys
            - 'level': corresponds to css class for indenting
            - 'text': text to dispaly for that entry
            - 'id': tag id it maps to
        main_toc: boolean indicating if main TOC

    Returns:
        HTML string of nested <ul> and <li> elements

    Note:
        This function uses recursion to handle nested heading levels.
        h1 is rendered as a special "Back to top" link.
    """

    # Filter to only include entries at or below max depth
    entries = [e for e in toc_entries if e["level"] <= TOC_MAX_DEPTH]

    html = '<ul class="toc-list">\n'

    # Intra-page TOC: Create anchor to top of document
    if not main_toc:
        html += f'  <li><a href="#top" class="toc-level-h1 top-link">↑ Top</a></li>\n'

    # create <li> for each heading
    for entry in entries:
        level = entry["level"]
        text = entry["text"]
        anchor_id = entry["id"]
        level_class = f"toc-level-h{level}"
        html += f'  <li><a href="#{anchor_id}" class="{level_class} chap-link">{text}</a></li>\n'

    html += "</ul>\n"
    return html


def create_chapter_toc_entries(
    html_content: str, max_depth: int = 4
) -> Tuple[str, List[Dict]]:
    """
    Parse HTML, add missing IDs to headings, and build TOC structure.

    Args:
        html_content: HTML string from markdown conversion.
        max_depth: Maximum heading level to include (1-4).

    Returns:
        Tuple of (modified_html, toc_entries) where toc_entries is a list of
        dicts with keys: level, text, id.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    toc_entries = []

    # Find all tags for TOC
    for tag in soup.find_all(TOC_TAGS):
        # if this is an <h1>, <h2>, etc. try to get number
        # else default to level 1 assumption
        level = 1
        if tag.name and tag.name[1].isdigit():
            level = int(tag.name[1])
        if level > max_depth:
            continue

        # Ensure tag has an ID
        if not tag.get("id"):
            tag["id"] = random_digit_string(5)

        # set default text for the entry if tag has no text (e.g. <hr>)
        entry_text = tag.get_text(strip=True) or "next"

        toc_entries.append(
            {
                "level": level,
                "text": entry_text,
                "id": tag.get("id"),
            }
        )

    return str(soup), toc_entries


def create_toc_entries(doc: Document, max_depth: int = 4) -> List[Dict]:
    """
    Build TOC entries for the document.

    -- Connection to javascript / How the TOC works --

    1. Each TOC entry corresponds to a Part or Chapter
    2. href attr assigned to Part or Chapter's id attr
    3. That id attr is also stored as a key in a dictionary
       that gets written to a javascript file; it's value
       is the HTML content that should be loaded when user
       clicks on that TOC link.

    Args:
        doc: Document object generated from inputfile JSON
        max_depth: Maximum heading level to include (1-4).

    Returns:
        toc_entries: a list of dicts with keys: level, text, id.
    """
    toc_entries = []

    # Document is either flat (chapters only)
    # or heirarchical (parts + chapters)
    # either .chapters or .parts attr is populated, not both

    # Flat structure: (no parts)
    for chapter in doc.chapters:
        toc_entries.append(
            {
                "level": 1,
                "text": chapter.name,
                "id": chapter.id,
            }
        )

    # Heirarchical structure: (has parts)
    for part in doc.parts:
        toc_entries.append(
            {
                "level": 1,
                "text": part.name,
                "id": part.id,
            }
        )
        for chapter in part.chapters:
            toc_entries.append(
                {
                    "level": 2,
                    "text": chapter.name,
                    "id": chapter.id,
                }
            )
    return toc_entries


def create_toc(doc: Document) -> str:
    toc_entries = create_toc_entries(doc, TOC_MAX_DEPTH)
    return render_toc(toc_entries, True)


# ============================================================================
# DOCUMENT GENERATION
# ============================================================================


def make_tags_navigable(html: str) -> str:
    """Find all navigable tags in document and add nav-target with id for js navigation.

    This function parses an HTML string, identifies all specified navigable tags
    (defined by NAV_TAGS constant), and adds both unique IDs and a 'nav-target'
    class to each tag that doesn't already have an ID. This enables JavaScript
    intra-page navigation functionality.
    (see following commit, under "TOC fundamentals" for explanation of js intra-page nav)
    https://github.com/bkuz114/pereplyot/commit/7f0660d0ce56bc9a8ab57785b9b642d603906d6f

    Args:
        html (str): The HTML string to process. Can be any valid HTML content.

    Returns:
        str: The modified HTML string with unique IDs and 'nav-target' classes
             added to all navigable tags. Tags that already had IDs will only
             receive the 'nav-target' class.

    Raises:
        BeautifulSoupParserError: If the HTML string cannot be parsed by BeautifulSoup.
        NameError: If NAV_TAGS constant is not defined in the module scope.

    Example:
        >>> html = '<div><h2>Section 1</h2><p>Content</p></div>'
        >>> NAV_TAGS = ['hr', 'h1', 'h2']
        >>> result = make_tags_navigable(html)
        >>> print(result)
        <div><h2 class="nav-target" id="abc12">Section 1</h2><p>Content</p></div>

    Note:
        - The NAV_TAGS constant must be defined in the module containing this function
        - IDs are generated using random_digit_string(5), which should be defined elsewhere
        - Existing IDs are preserved; new IDs are only added to tags without one
        - The function uses BeautifulSoup for HTML parsing and manipulation
    """

    # Parse the HTML string
    soup = BeautifulSoup(html, "html.parser")

    # Find all HTML tags for intra-page navigation
    for tag in soup.find_all(NAV_TAGS):
        # assign id if not present (js uses for debug logs)
        if not tag.get("id"):
            tag["id"] = random_digit_string(5)
        # add .nav-target class (for js intra-page navigation)
        beautiful_soup_utils.add_classes(tag, ["nav-target"])

    # convert back to string to return
    return str(soup)


def template_html(
    template_path: Path,
    content: str,
    frontmatter: Dict[str, str],
    toc_html: str,
    asset_path_prefix: str,
    hide_navigation: bool,
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
        hide_navigation: boolean if True, hides section TOC button

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
    chapter_toc_button_inline_style = ""
    if hide_navigation:
        chapter_toc_button_inline_style = 'style="display: none;"'
    substitutions = {
        "content": content,
        "toc": toc_html,
        "asset_path_prefix": asset_path_prefix,
        "chapter_toc_button_inline_style": chapter_toc_button_inline_style,
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


def write_html_file(content: str, output: Path, force: bool) -> Path:
    """
    Write the final HTML file, checking for existing file and --force flag.

    Args:
        content: Final HTML string.
        output: Path to write html file to
        force: Whether to overwrite existing file.

    Returns:
        Path to file written

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

    return output


def create_home(doc: Document, style: str) -> str:
    """Creates HTML for initial page load splash screen.

    Args:
        doc: Document object generated from inputfile JSON.
        style: string indicating what style (options: basic, descriptive)

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

    homepage_descriptive = f"""
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

    homepage_basic = f"""
        <div class="splash-container basic">
            <h1 class="splash-title">{title}</h1>

            <div class="splash-meta">
                {metadata_html}
            </div>

            <div class="splash-start-wrapper">
                <button id="splash-start" class="splash-start-btn">Start</button>
            </div>
        </div>
        """

    if style == "basic":
        return homepage_basic
    else:
        return homepage_descriptive


def convert_markdown_to_html(filepath: str) -> str:
    """
    Convert Markdown file to HTML using python-markdown.

    Args:
        filepath: Path to a markdown file

    Returns: HTML string with heading IDs added
    """
    valid_extensions = [".md", ".markdown"]
    if not filepath.exists():
        raise Exception(f".md file {filepath} does not exist!")
    if filepath.suffix.lower() not in valid_extensions:
        raise Exception(f"File is not markdown! {filepath}")

    # extract content
    raw_content = read_file(filepath)

    # remove YAML frontmatter
    metadata, md_content = parse_frontmatter(raw_content)

    # Convert markdown to HTML
    raw_html = markdown.markdown(md_content, extensions=MD_EXTENSIONS)

    return raw_html


def convert_raw_text_to_html(raw_text: str, indent: int = 0) -> str:
    """
    Convert raw text string to HTML with paragraph preservation and exact leading whitespace.

    Behavior:
        - Splits text into paragraphs on double newlines (blank lines).
        - Each paragraph is wrapped in <p> tags.
        - Single newlines within a paragraph become <br> tags.
        - Leading spaces/tabs on lines are preserved visually
          by converting each space to &nbsp; and each tab to 4 &nbsp;.
        - If the first line has no leading whitespace, no &nbsp; prefix is added.
        - cyrillic style << >>, « » converted to <em> </em> tags

    Args:
        raw_text: string to convert to HTML
        indent: int to control indentation of new lines in raw text.
            If > 0, all lines will be indented that many spaces.
            NOTE: Overrides any leading spaces currently present.

    Returns:
        HTML string with paragraphs, line breaks, and preserved leading indentation.
    """

    # replacements to make on the raw text
    replacements = []

    # Normalize Windows line endings to Unix-style
    replacements.append(["\r\n", "\n"])

    # convert << >>, « » to <em> </em>
    replacements.extend(
        [["<<", "<em>"], [">>", "</em>"], ["«", "<em>"], ["»", "</em>"]]
    )

    raw_text = sequential_replacements(raw_text, replacements)

    # lines with only * or - (e.g. ***, --) convert to <hr>
    # Notes:
    # 1. must be surrounded by \n to avoid catching valid inline chars e.g. "Then - he paused"
    # 2. pad <hr> with \n\n so surrounding text will be interpreted as paragraphs on next split
    raw_text = re.sub(r"(?<=\n)[*-]+(?=\n)", r"\n\n<hr>\n\n", raw_text)

    # Split on double newlines (blank lines) to identify paragraphs
    paragraphs = re.split(r"\n\s*\n", raw_text)

    html_parts = []
    for para in paragraphs:
        para = para.strip("\n")
        if not para.strip():  # Skip empty paragraphs
            continue

        # User-added <hr>: add and continue to avoid empty line on --indent option
        # (will preprend &nsbp; to "<hr>" which causes blank &nsbp; line above <hr>)
        # note: only check startswith "<hr" (not == "<hr>") in case css classes, etc.
        if para.strip().startswith("<hr"):
            html_parts.append(para)
            continue

        lines = para.split("\n")
        if not lines:
            continue

        # preserve leading whitespace in lines
        for i, line in enumerate(lines):
            preserve_prefix = ""
            num_spaces = 0
            if indent:
                # add uniform num of spaces to all lines,
                # regardless of how many currently present.
                num_spaces = indent
            else:
                # Convert leading spaces/tabs to &nbsp; entities
                for ch in line:
                    if ch == " ":
                        num_spaces += 1
                    elif ch == "\t":
                        num_spaces += 4
                    else:
                        break  # Stop at first non-whitespace character
            preserve_prefix += "&nbsp;" * num_spaces
            lines[i] = f"{preserve_prefix}{line}"

        # Rebuild paragraph with <br> for newlines
        para_with_br = "<br>\n".join(lines)
        html_parts.append(f"<p>{para_with_br}</p>")

    return "\n".join(html_parts)


def convert_txt_to_html(filepath: Path, indent: int) -> str:
    """
    Convert .txt file to HTML.
    (see docstring of convert_raw_text_to_html for formatting specifics)

    Args:
        filepath: Path to .txt file
        indent: int. Indents new lines in .txt, .rtf by this many spaces
            in final rendered HTML (overrides existing leading spaces to
            make document indentation uniform).

    Returns:
        HTML string with paragraphs, line breaks, and preserved leading indentation.

    Raises:
        Exception: If file does not exist or is not a .txt file.
    """
    if not filepath.exists():
        raise Exception(f".txt file {filepath} does not exist!")
    if not filepath.suffix.lower() == ".txt":
        raise Exception(f"File is not .txt! {filepath}")

    raw_text = read_file(filepath)
    return convert_raw_text_to_html(raw_text, indent)


def convert_docx_to_html(filepath: Path) -> str:
    """
    Convert a .docx file to HTML, preserving headings, lists, bold/italic,
    tables, and basic structure.

    Args:
        filepath: Path to .docx file

    Returns:
        HTML string
    """
    if not filepath.exists():
        raise Exception(f".docx file {filepath} does not exist!")
    if not filepath.suffix.lower() == ".docx":
        raise Exception(f"File is not .docx! {filepath}")
    result = mammoth.convert_to_html(filepath)
    # Log any warnings (e.g., unrecognized styles)
    for message in result.messages:
        logger.warning(f"⚠️  Warning: [mammoth] {message}")
    return result.value


def convert_rtf_to_html(filepath: Path, indent: int) -> str:
    """
    Convert Microsoft .rtf file to HTML. Experimental -- use at own risk.

    Limitations:
    - formatting (bold, italic, etc.) NOT preserved
    - certain complex writeups will fail (e.g. write plaintext in Word ->
      save as rtf -> likely fails)
    - certain chars do not render (emdash, etc.)

    Args:
        filepath: Path to .docx file
        indent: int. Indents new lines in .txt, .rtf by this many spaces
            in final rendered HTML (overrides existing leading spaces to
            make document indentation uniform).

    Returns:
        HTML string
    """
    if not filepath.exists():
        raise Exception(f".docx file {filepath} does not exist!")
    if not filepath.suffix.lower() == ".rtf":
        raise Exception(f"File is not .rtf! {filepath}")

    with open(filepath, "rb") as f:
        rtf_bytes = f.read()

    # Decode as ascii, ignoring errors (RTF is 7-bit)
    rtf_bytes = rtf_bytes.decode("ascii", errors="ignore")
    text_string = rtf_to_text(rtf_bytes)

    return convert_raw_text_to_html(text_string, indent)


def post_process_file_html(html: str) -> str:
    return f'<div class="file-section">{html}</div>'


def post_process_chapter_html(html: str, title: str) -> str:
    """Wrap chapter HTML in a div and generate a unique identifier for it

    Args:
        html: HTML string of the chapter's content (made up of all its files)
        title: string chapter of title

    Returns:
        string of updated HTML
    """
    return f'<div class="chapter-section"><h2 class="chapter-title">{title}</h2>{html}</div>'


# ============================================================================
# HANDLING OF ASSETS AND OTHER ARTIFACTS
# ============================================================================


def copy_assets_to_output(
    assets_path: Path, assets_dest_dir: Path, force: bool = False, nuclear: bool = False
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
        nuclear: If True, uses aggressive deletion that strips read-only
                 permissions before retrying (Windows only). Implies force.
                 This is used when force alone fails (see 62b1330 and related)

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
        try:
            if force:
                remove_path(assets_dest_dir, force, nuclear)
            else:
                raise FileExistsError(
                    f"Destination already exists: {assets_dest_dir}\n"
                    f"Use force=True to overwrite."
                )
        except Exception as e:
            raise RuntimeError(f"Failed to remove existing assets dir: {e}")

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


def process_chapter(chapter: Chapter, strict: bool, indent: int) -> Tuple[str, int]:
    """
    Generates HTML content for a single Chapter (which can be
    comprised of multiple FileRef objects)

    Arguments
        chapter: Chapter to get HTML string for
            (Note: Chapter objects are part of a Document object -- the object
            created via inputfile.py when pasing manifest JSON)
        strict: boolean if True, fail on any file processing failure
        indent: int. Indents new lines in .txt, .rtf by this many spaces
            in final rendered HTML (overrides existing leading spaces to
            make document indentation uniform).

    Returns
        Tuple of [str, int]: HTML content + number of failed files
    """

    html = ""
    failed_count = 0

    for i, fileRef in enumerate(chapter.files):
        try:
            # HTML for this file
            file_html = ""
            filepath = fileRef.path
            file_ext = filepath.suffix.lower()
            if file_ext == ".txt":
                file_html = convert_txt_to_html(filepath, indent)
            elif file_ext == ".docx":
                file_html = convert_docx_to_html(filepath)
            elif file_ext == ".rtf":
                file_html = convert_rtf_to_html(filepath, indent)
            elif file_ext == ".markdown" or file_ext == ".md":
                file_html = convert_markdown_to_html(filepath)
            file_html = post_process_file_html(file_html)

            # add <hr> if multiple files
            if i > 0:
                html += "<hr>"
            html += file_html

        except Exception as e:
            logger.error(f"   ❌ Failed: {fileRef.path} - {e}")
            failed_count += 1
            if strict:
                raise  # Fail fast in strict mode

    return html, failed_count


def process_chapters(
    chapters: List[Chapter],
    strict: bool,
    indent: int,
    prev_chapter_id: str | None,
    next_chapter_id: str | None,
) -> Tuple[Dict[str, Dict[str, str]], int]:
    """
    Iterates through a list of Chapter obejcts (coming from Document -- the object
    created from input JSON manifest file), raw content,
    converts it to an HTML string, and returns a dictionary of that content
    (mapped to unique keys)

    The HTML strings generated will NOT get embedded into final HTML file;
    the dictionary returned by this function instead gets written to a javscript
    file, and javscript dynamically loads the content when user clicks TOC links

    Args:
        doc: Document object generated from input JSON file.
        strict: If True, abort on first error and re-raise the exception.
            If False, log errors and continue processing remaining files.
        indent: int. Indents new lines in .txt, .rtf by this many spaces
            in final rendered HTML (overrides existing leading spaces to
            make document indentation uniform).
        prev_chapter_id: ID of the chapter immediately preceding the first
            chapter in this list. Used to weave chapter sequences across
            Parts in hierarchical documents. Pass None if this is the first
            list of chapters (no preceding chapter), or for flat documents.
        next_chapter_id: ID of the chapter immediately following the lasti
            chapter in this list. Used to weave chapter sequences across
            Parts in hierarchical documents. Pass None if this is the last
            list of chapters (no following chapter), or for flat documents.

    Returns:
        Tuple containing:
            1. Dict[str, Dict[str, str]]: Maps chapter.id to chapter data, where
               chapter data contains:
               - "content": HTML string for the chapter
               - "prev": (optional) ID of previous chapter (for navigation)
               - "next": (optional) ID of next chapter (for navigation)
            2. count of files that failed to procss
    """

    html = {}
    failed_count = 0

    for i, chapter in enumerate(chapters):
        chapter_html, failed_files = process_chapter(chapter, strict, indent)
        failed_count += failed_files
        # post-process (Add title, etc)
        chapter_name = f"Chapter: {chapter.name}"
        # wrap in div and get the id attr assigned to it
        chapter_html = post_process_chapter_html(chapter_html, chapter_name)
        # create a TOC for the chapter with ids added in
        chapter_html, chapter_toc_entries = create_chapter_toc_entries(chapter_html)
        chapter_toc = render_toc(chapter_toc_entries)
        # set up intra-page navigation within page HTML
        chapter_html = make_tags_navigable(chapter_html)

        # id of previous chapter (either passed in
        # from previous part, or prev chapter in this chapter list)
        prev_id = None
        if i == 0:
            # this is the first chapter in this chapter list
            # so the previous chapter is the last chapter
            # in the last part (if any)
            prev_id = prev_chapter_id
        else:
            prev_id = chapters[i - 1].id

        # id of next chapter (either passed in from
        # next part, or next chapter in this chapter list)
        next_id = None
        if i == len(chapters) - 1:
            # this is last chapter in this chapter list
            # so the next chapter is the first chapter
            # in the next part (if any)
            next_id = next_chapter_id
        else:
            next_id = chapters[i + 1].id

        # construct dictionary to map chapter id to
        #
        # CAUTION! DO NOT CHANGE THESE ATTR NAMES!
        # scripts.js depends on them.
        chapter_data = {"content": chapter_html, "toc": chapter_toc}
        if prev_id:
            chapter_data["prev"] = prev_id
        if next_id:
            chapter_data["next"] = next_id

        # add to main content html
        html[chapter.id] = chapter_data

    return html, failed_count


def process_files(doc: Document, strict: bool, indent: int) -> Dict[str, str]:
    """
    Returns a dictionary mapping unique chapter ids to the HTML content
    created for that chapter (made up of its individual files, converted
    to HTML strings)

    Args:
        doc: Document object generated from input JSON file.
        strict: If True, abort on first error and re-raise the exception.
            If False, log errors and continue processing remaining files.
        indent: int. Indents new lines in .txt, .rtf by this many spaces
            in final rendered HTML (overrides existing leading spaces to
            make document indentation uniform).

    Returns:
        a dictionary of {unique_ID : HTML_content} pairs (one for each "chapter"), where:
        - unique_ID: an id generated for the constructed chapter
        - HTML_content: HTML string of all data for a chapter (chapters
          can have multiple files)
    """
    # Document has either "parts" or "chapter" list populated, but not both

    # dictionary to send to javascript for dynamically opening
    # content when user clicks a TOC link
    html_dict = {}
    total_failed = 0
    # id of first chapter in binder (for special "first" key in dictionary)
    first_id = None

    # Scenario 1: has parts
    if doc.parts:
        for i, part in enumerate(doc.parts):
            # get id of last chapter in previous part
            prev_part_last_chap_id = None
            if i > 0:
                prev_part_chapters = doc.parts[i - 1].chapters
                prev_part_last_chap_id = prev_part_chapters[
                    len(prev_part_chapters) - 1
                ].id
            # get id of first chapter in next part
            next_part_first_chap_id = None
            if i < len(doc.parts) - 1:
                next_part_chapters = doc.parts[i + 1].chapters
                next_part_first_chap_id = next_part_chapters[0].id
            chapters_html, chapters_failed_count = process_chapters(
                part.chapters,
                strict,
                indent,
                prev_part_last_chap_id,
                next_part_first_chap_id,
            )
            # add part id as key to html_dict: its value
            # will be the HTML content it opens to --
            # should be the first chapter in this part
            html_dict[part.id] = chapters_html[part.chapters[0].id]
            total_failed += chapters_failed_count
            # add next set of chapter id / contents to html dictionary for js
            html_dict = html_dict | chapters_html

        # save id of first chapter
        first_id = doc.parts[0].chapters[0].id

    # Scenario 2: flat structure (only chapters, no parts)
    if doc.chapters:
        # only html_dict and total_failed are needed
        html_dict, total_failed = process_chapters(
            doc.chapters, strict, indent, None, None
        )
        # save id of first chapter
        first_id = doc.chapters[0].id

    # create special section for first chapter
    html_dict["first"] = html_dict[first_id]

    logger.info(
        f"\n✅ Processed {len(doc.files) - total_failed} of {len(doc.files)} files"
    )
    if total_failed > 0 and not strict:
        logger.error(f"   ⚠️  {total_failed} file(s) failed")

    return html_dict


def generate_binder(
    doc: Document,
    output_file: Path,
    template_path: Path,
    assets_path: Path,
    final_assets_dir: Path,
    js_helper_path: Path,
    force: bool,
    nuclear: bool,
    strict: bool,
    home_style: str,
    hide_navigation: bool,
    indent: int,
) -> Path:
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
        nuclear: If True, uses aggressive deletion that strips read-only
                 permissions before retrying (Windows only). Implies force.
        strict: If True, abort on first error and re-raise the exception.
            If False, log errors and continue processing remaining files.
        home_style: str indicating style for homepage ("basic", "descriptive")
        hide_navigation: boolean if True, hides section TOC button
        indent: int. Indents new lines in .txt, .rtf by this many spaces
            in final rendered HTML (overrides existing leading spaces to
            make document indentation uniform).

    Returns:
        Path to generated file
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
    content_dict = process_files(doc, strict, indent)

    # create TOC
    toc = create_toc(doc)

    # create splash page to load on page load
    splash_html = create_home(doc, home_style)

    # add splash page HTML to content dict
    # - don't change "start"! scripts.js depends on it
    # - don't change "content" -- must be consistent with
    #   rest of content_dict
    content_dict["start"] = {"content": splash_html}

    # Render template
    final_html = template_html(
        template_path,
        splash_html,
        metadata,
        toc,
        asset_path_prefix,
        hide_navigation,
    )

    # Write output
    binder = write_html_file(final_html, output_file, force)

    # Copy assets once after all files processed (or before, doesn't matter)
    copy_assets_to_output(assets_path, final_assets_dir, force, nuclear)

    # Write js helper file (do after copying assets in case it lives there)
    write_javascript_helper(content_dict, js_helper_path)

    return binder


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
        description="Generate an offline HTML page for navigating a binder of documents (.txt, .md, .markdown, or .docx)",
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
        "-n",
        "--nest",
        required=False,
        action="store_true",
        help="Per-run directories created.",
    )
    parser.add_argument(
        "-u",
        "--use-title",
        required=False,
        action="store_true",
        help="Use project title in dir (if --nest) or filename (if no --nest).",
    )
    parser.add_argument(
        "-t",
        "--timestamp",
        required=False,
        action="store_true",
        help="Timestamp dir (if --nest) or file (if no --nest)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file if it exists",
    )
    parser.add_argument(
        "--nuclear",
        action="store_true",
        help="USE AT YOUR OWN RISK. Force delete output directory by removing "
        "read-only permissions. Only use if --force fails with 'Access denied'.",
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
        "--quiet",
        action="store_true",
        help="Suppress all non-error output (useful for scripting)",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Open generated HTML file in user's default browser upon completion",
    )
    parser.add_argument(
        "--home",
        type=str,
        choices=["basic", "descriptive"],
        default="descriptive",
        help="Style of splash page",
    )
    parser.add_argument(
        "--no-navigation",
        action="store_true",
        help="Hide section TOC button from the header",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=0,
        help="Indent all new lines in .txt, .rtf files by this many spaces (Note: overrides existing leading whitespace to make indentation uniform throughout binder.)",
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

    # parse input JSON into Document object
    input_file = args.input.resolve()  # resolve rel cwd
    doc = Document.from_json(input_file)
    title = doc.title

    # determine output directory
    output_file, output_dir = determine_output(
        output_dir, title, args.nest, args.use_title, args.timestamp
    )

    # delete output dir if exists and --clean provided
    if args.clean:
        if not args.force and not args.nuclear:
            logger.error("❌ Error: --clean requires --force or --nuclear")
            sys.exit(1)
        if output_dir.exists():
            remove_path(output_dir, args.force, args.nuclear)
            logger.info(f"🧹 Cleaned output directory: {output_dir}")

    # Final assets directory (shared across all files)
    final_assets_dir = output_dir / "assets"

    # Path to write helper javascript file to
    # (for switching content via TOC)
    js_helper_path = final_assets_dir / "js/sections.js"

    # Process all the files
    binder = generate_binder(
        doc,
        output_file,
        template_path,
        assets_path,
        final_assets_dir,
        js_helper_path,
        args.force,
        args.nuclear,
        args.strict,
        args.home,
        args.no_navigation,
        args.indent,
    )

    # optionally open in browser
    if args.browser:
        webbrowser.open(binder)


if __name__ == "__main__":
    main()
