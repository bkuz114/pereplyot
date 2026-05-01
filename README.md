# Переплет (bookbinder)

Bundle multiple documents (.txt, .md, .docx) into a single, beautiful HTML viewer with hierarchical table of contents and smooth content switching.

## Features

- **Multiple file types** – Supports `.txt`, `.md`, and `.docx`
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

Output is written to `dist/binder.html`.

### With custom output directory

```bash
pereplyot manifest.json --output site/
```

### Force overwrite

```bash
pereplyot manifest.json --force
```

### With custom template

```bash
pereplyot manifest.json --template my-template.html
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
pereplyot examples/fishing_doc.json
```

## File Types

| Extension | Conversion | Output |
|-----------|------------|--------|
| `.txt` | Plain text | Wrapped in `<p>` tags |
| `.md` | Markdown | Converted to HTML via python-markdown |
| `.docx` | Microsoft Word | Converted via python-docx |

## Output Structure

```
dist/
├── binder.html          # Main HTML file
└── assets/
    ├── css/
    │   ├── styles.css      # Core styles
    │   └── themes.css      # Theme variables
    └── js/
        ├── scripts.js      # TOC interaction, content swapping
        └── sections.js     # Generated content dictionary
```

## How It Works

1. **Parse manifest** – Load JSON and build document structure
2. **Convert files** – Each file converted to HTML string
3. **Group by chapter** – Files in same chapter combined (with `<hr>` between)
4. **Generate TOC** – Hierarchical navigation from document structure
5. **Write `sections.js`** – Dictionary mapping chapter IDs to HTML content
6. **Write `binder.html`** – Shell with TOC (content loaded dynamically)
7. **Click TOC** – JavaScript swaps content with smooth animation

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
