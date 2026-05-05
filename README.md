# Переплет (bookbinder)

[![PyPI version](https://badge.fury.io/py/pereplyot.svg)](https://pypi.org/project/pereplyot/)
[![Python versions](https://img.shields.io/pypi/pyversions/pereplyot.svg)](https://pypi.org/project/pereplyot/)

Bundle multiple documents (.txt, .md, .docx, and .rtf) into a single, beautiful HTML viewer with hierarchical table of contents and smooth content switching.

## Features

- **Multiple file types** – Supports `.txt`, `.md`, `.docx`, and `.rtf`
- **JSON manifest** – Define document structure (chapters → files)
- **Single HTML output** – Everything in one file (plus shared assets)
- **Hierarchical TOC** – One entry per chapter, clean navigation
- **Smooth content switching** – Animated transitions via JavaScript
- **Themes** – Built-in theme toggle to switch color themes for site
- **Responsive design** – Works on desktop and mobile
- **No URL hashing** – Clean back button behavior
- **Customizable** – Bring your own template, CSS, or JavaScript

## Installation

```bash
pip install pereplyot
```

## Usage

### Basic usage

```bash
pereplyot manifest.json
```

Output is written to `dist/index.html`.

### With custom output directory (see more output options [here](#output))

```bash
pereplyot manifest.json --output site/
```

### Force overwrite

```bash
pereplyot manifest.json --force
```

### Automatically open generated file in default web browser upon completion

```bash
pereplyot manifest.json --browser
```

### With custom template

```bash
pereplyot manifest.json --template my-template.html
```

### Minimal "home" screen with only title, author

```bash
pereplyot manifest.json --home basic
```

## Manifest Format

Create a JSON file defining your document structure:

```json
{
  "title": "My Portfolio",
  "description": "A collection of my work",
  "author": "Your Name",
  "chapters": [
    {
      "title": "Chapter 1: Introduction",
      "files": [
        {"path": "docs/intro.md", "name": "Getting Started"},
        {"path": "docs/background.txt", "name": "Background"},
        {"path": "docs/report.docx", "name": "Initial Report"}
      ]
    },
    {
      "title": "Chapter 2: Deep Dive",
      "files": [
        {"path": "docs/analysis.md", "name": "Data Analysis"},
        {"path": "docs/conclusions.txt", "name": "Conclusions"}
      ]
    }
  ]
}
```

### Manifest Fields

| Field | Required | Description |
|-------|----------|-------------|
| `title` | Yes | Document title (appears in header and browser tab) |
| `description` | No | Meta description for SEO |
| `author` | No | Author name (can be used in custom templates) |
| `chapters` | Yes | Array of chapters |
| `chapters[].title` | Yes | Chapter title (appears in TOC) |
| `chapters[].files` | Yes | Array of files in this chapter |
| `files[].path` | Yes | Path to document (relative to manifest location) |
| `files[].name` | No | Display name (falls back to filename) |

### Example manifest files

A collection of example manifest files and documents can be found in `examples/` directory:

```
git clone https://github.com/bkuz114/pereplyot.git
pip inistall pereplyot
pereplyot examples/the-fishing-book/manifest.json
```

## File Types

| Extension | Conversion | Output |
|-----------|------------|--------|
| `.txt` | Plain text | Wrapped in `<p>` tags |
| `.md` | Markdown | Converted to HTML via python-markdown |
| `.docx` | Microsoft Word | Converted via python-docx |
| `.rtf` | Microsoft rtf | Converted via rtfparse |

## How It Works

1. **Parse manifest** – Load JSON and build document structure
2. **Convert files** – Each file converted to HTML string
3. **Group by chapter** – Files in same chapter combined (with `<hr>` between)
4. **Generate TOC** – Hierarchical navigation from document structure
5. **Write `sections.js`** – Dictionary mapping chapter IDs to HTML content
6. **Write `index.html`** – Shell with TOC (content loaded dynamically)
7. **Click TOC** – JavaScript swaps content with smooth animation

## Output

### Default Behavior

Without additional flags, pereplyot writes to `dist/index.html` with supporting assets in `dist/assets/`:

```
dist/
├── index.html
└── assets/
	├── css/
	│   ├── styles.css
	│   └── themes.css
	└── js/
		├── scripts.js
		└── sections.js
```

### Customizing Output Location

Use `--output <directory>` to change the base output directory:

```bash
pereplyot input.json --output ./reports
```

```
reports/
├── index.html
└── assets/...
```

### Advanced Output Control

Three optional flags give fine-grained control over filenames and directory structure:

| Flag | Effect |
|------|--------|
| `--timestamp` | Adds timestamp (YYYY_MM_DD-HH_MM_SS) to filename or directory |
| `--use-title` | Uses document title in filename or directory name |
| `--nest` | Creates per-run subdirectories (requires `--timestamp` or `--use-title`) |

These flags combine as follows (examples use default `dist/` as base):

| `--use-title` | `--timestamp` | `--nest` | Output within `dist/` |
|---------------|---------------|----------|----------------------|
| — | — | — | `index.html` |
| — | ✓ | — | `2025_05_05-14_30_22.html` |
| ✓ | — | — | `my_project.html` |
| ✓ | ✓ | — | `my_project_2025_05_05-14_30_22.html` |
| ✓ | — | ✓ | `my_project/index.html` |
| — | ✓ | ✓ | `2025_05_05-14_30_22/index.html` |
| ✓ | ✓ | ✓ | `my_project/2025_05_05-14_30_22/index.html` |

### Examples

```bash
# Simple custom location
pereplyot input.json --output ./docs

# Timestamped file (no overwrites)
pereplyot input.json --timestamp

# Project directory with timestamped subdirectory
pereplyot input.json --use-title --timestamp --nest --output ./archive
```

### Notes

- `--nest` requires either `--timestamp` or `--use-title` (or both)
- Document titles are sanitized: spaces become underscores, text is lowercased
- Assets are always copied to a `dist/assets/` subdirectory relative to the final output file

## Customization

### Custom Template

Create your own HTML template with these placeholders:

| Placeholder | Description |
|-------------|-------------|
| `{{ title }}` | Document title from manifest |
| `{{ description }}` | Meta description |
| `{{ toc }}` | Generated table of contents |
| `{{ asset_path_prefix }}` | Relative path to assets (e.g., `assets/` or `../assets/`) |

### Custom CSS/JS

Replace the default assets with your own:

```bash
pereplyot manifest.json --assets path/to/my/assets
```

Your assets directory should contain `css/` and `js/` subdirectories.

## HTML in source documents

HTML tags are passed through to the output without escaping. This allows you to use rich formatting (bold, italic, lists, tables, etc.) directly in your source files across `.txt`, `.rtf`, and `.md` formats.

**Example:**

Source:

```html
This file has <b>HTML tags</b>.
```

Rendered output:

> This file has **HTML tags**.

> **Note:** Because HTML is not escaped, be mindful of tag balancing and
> avoid raw user-generated content unless properly sanitized.

## Development

### Prerequisites

- Python 3.9+
- Git

### Clone and install

```bash
git clone https://github.com/bkuz114/pereplyot.git
cd pereplyot
pip install -e .
```

### Build distribution

```bash
./bin/build.sh
```

## License

MIT License – see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [python-markdown](https://python-markdown.github.io/)
- Document conversion via [python-docx](https://python-docx.readthedocs.io/)
- Template rendering inherited from [renderkind](https://github.com/bkuz114/renderkind)
- JSON parsing via vendored [inputfile-parser](https://github.com/bkuz114/inputfile-parser)
- rtf parsing via striprtf [striprtf](https://pypi.org/project/striprtf/)
- docx parsing via mammoth [mammoth](https://pypi.org/project/mammoth/)
