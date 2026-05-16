# Changelog

All notable changes to `pereplyot` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0]

### Formatting Updates
  - Convert `-` and `--` to emdash (`—`) in `.txt` and `.rtf` docs (Note: only converts if surrounded by whitespace to avoid converting compound words) (0882eee) 
  - Convert `...` (three periods) to `…` (horizontal ellipsis char) in `.txt` and `.rtf` docs (8f73c91)

### Fixed
- Windows `--nuclear` deletion fails with two separate errors:
  1. `TypeError: make_path_writable() takes 2 positional arguments but 3 were given`
  2. `NameError: name 'stat' is not defined`
  - The `onerror` handler for `shutil.rmtree()` now accepts the required `excinfo` parameter
  - The missing `import stat` statement is now present.
  - Fixes permission-stripping retry mechanism on Windows when standard `--force` fails with access denied errors
  - **Note**: These errors ONLY occured when `shutil.rmtree()` encountered an error (and thus the faulty callback is called)
  - See commit b713441

## [1.1.0]

- **Support for Parts**
  - Adds support for heirarchical JSON specifying parts and chapters, rather than just chapters (7f0660d)
  - `root` can be specified on parts (evaluated rel doc root if provided, else rel JSON source) (e181f42)

- **Intra-page Navigation**
  - Chapters have their own navigation via a new TOC panel accessed through § button on right of header (hidden for docs with no headers) (5ee8e7e)
  - ◀ ▶ buttons in header allow quick navigation between headers and `<hr>` tags (cebcd36)

- **Inter-page Navigation**
  - ◀◀ ▶▶ buttons in header allow quick navigation between chapters (641803a)

- **Formatting Upgrades: .txt, .rtf**
  - Parsed txt files have paragraph breaks preserved (466b267)
  - Paragraph indenting preserved (466b267)
  - Cyrillic style emphasis (<< >>, « ») converted to `<em>` `</em>` tags (3fdbac3)
    (possibly make this a CLI option in the future)
  - `*` and `-` lines (lines with only these chars) get converted to `<hr>` and become part of intra-page navigation (1837090)

- **Formatting Upgrades: .docx**
  - Tables, italics, bold, headings now preserved (f39abd9)

- **CLI upgrades**
  - `--browser` flag to open generated HTML in the browser upon completion. (80306c9)
  - `--home` option to select home page styling ("basic" or "descriptive") (61a1d5e)
  - `--no-navigation` flag to hide § button from the header (80a3277, 7be4432) 
  - `--indent INTEGER` option to uniformly indent all new lines in `.txt`, `.rtf` (c2fb9d8)
  - `--timestamp`, `--use-title`, and `--nest` for full control over file output (0571a89)
  - `--nuclear` flag for aggressive deletion of previous builds (implies `--force`), to help with intermittent '[WinError 5] Access is denied' errors. Strips READONLY permissions on `shutil.rmtree` errors and retries (1b873ec) 

- **Output Control Upgrades**
  - Default output file renamed from `binder.html` to `index.html` for cleaner URLs (0571a89)
  - New flags `--timestamp`, `--use-title`, and `--nest` provide flexible control over output filenames and directory structure (0571a89)
  - Output can now be organized by project title, timestamp, or nested subdirectories (e.g., `project/2025_05_05-14_30_22/index.html`)
  - See README for full flag combination matrix

- **MINIMAL rtf support via striprtf (Experimental)**
  - Adds support for .rtf documents via `striprtf` with known limitations:
    - formatting (bold, italic, font size, etc.) not supported
	- certain complex writeups will not render (example: open Word -> plaintext -> save as rtf -> won't render)
  - Cyrillic is being preserved correctly.
  - This is a starting point only (original implementation with rtfparse mangled Cyrillic; striprtf appears to be preserving).
  - Commit 58d721e, 01046b0 

- **Themes**
  - Addition of four new themes: sollarYellow, sollarBlue, plum, midnight (84e558c)

- **Minor fixes**
  - Check for both `.md` and `.markdown` files (0c43c12)

- **Example Binders**
  - Replaced generic lorem ipsum text files with realistic test fixtures (96f6eee)
  - Example book `the-fishing-book` (96f6eee)
  - Example book `notes-for-the-stranger` (4e3c172) 

### Added

## [1.0.0] - 2026-05-01

### Added

- **Initial release of Pereplyot**
  - Bundle multiple documents (.txt, .md, .docx) into a single HTML viewer
  - JSON manifest defines document structure (chapters → files)
  - Hierarchical table of contents (one entry per chapter)
  - Smooth animated content switching via JavaScript
  - Content stored in separate `sections.js` (not embedded in HTML)
  - Inherited theming from renderkind (dark mode, responsive design)
  - No URL hashing (clean back button behavior)

- **Supported file types**
  - `.txt` – Plain text wrapped in `<p>` tags
  - `.md` – Markdown conversion via python-markdown
  - `.docx` – Microsoft Word documents via python-docx

- **CLI interface**
  - `pereplyot manifest.json` – Build from manifest
  - `--output DIR` – Specify output directory (default: `dist/`)
  - `--force` – Overwrite existing files
  - `--template PATH` – Custom HTML template
  - `--assets PATH` – Custom assets directory
  - `--strict` – Require frontmatter in markdown files
  - `--mode MODE` – Document mode for markdown (document/wiki)

- **Architecture features**
  - Chapters grouped into single content sections
  - Multiple files per chapter separated by `<hr>` (single file = no `<hr>`)
  - Content dictionary written to `assets/js/sections.js`
  - JavaScript swaps content on TOC click with animation
  - Assets copied automatically to output directory

### Changed

- N/A (initial release)

### Fixed

- N/A (initial release)

### Deprecated

- N/A (initial release)

### Removed

- N/A (initial release)

### Security

- No security-related changes in this release

---

[1.0.0]: https://github.com/bkuz114/pereplyot/releases/tag/v1.0.0
[1.1.0]: https://github.com/bkuz114/pereplyot/releases/tag/v1.1.0
[1.2.0]: https://github.com/bkuz114/pereplyot/releases/tag/v1.2.0
