# Changelog

All notable changes to `pereplyot` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
