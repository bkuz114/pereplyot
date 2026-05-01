---
title: "renderkind Demo & Documentation"
description: "A complete demonstration of renderkind features including frontmatter, tables of contents, tables, code blocks, and custom HTML."
---

# renderkind Demo & Documentation

Welcome to the `renderkind` demo. `renderkind` is a markdown to HTML genereator: It generates responsive, offline webpages with easy navigation and theme selection.

This file demonstrates all major features of the tool.

## Features Overview

| Feature | Status | Notes |
|---------|--------|-------|
| YAML Frontmatter | ✅ Supported | Title, description, custom fields |
| Build-time TOC | ✅ Supported | h1-h4 headings |
| Responsive Template | ✅ Supported | Default template included |
| Responsive Themes | ✅ Supported | Via external JS or custom implementation |
| Tables | ✅ Supported | Standard markdown tables |
| Code Blocks | ✅ Supported | Fenced code blocks with syntax highlighting |
| Raw HTML | ✅ Supported | Passes through unchanged |

## Frontmatter Example

This document includes frontmatter at the top:

```yaml
---
title: "renderkind Demo & Documentation"
description: "A complete demonstration of renderkind features..."
---
```

All frontmatter fields are passed to the template as `{{field_name}}` placeholders.

## Headings and TOC

A table of contents is automatically generated in your finished page. Click the "TOC" button on the top left of this page; on desktop, it will appear from the left, while on smaller screens it will be a top down reveal. Click on sections in the TOC to smooth scroll to that section.

### This is an h3

It appears indented under its parent h2 in the TOC.

#### This is an h4

It appears double-indented under its parent h3.

## Color Themes

Click the themes dropdown on the top right of this page to switch the color theme displayed.

*For advanced users: alter theme declarations via `assets/css/themes.css`.*

## Tables

Standard markdown tables are supported:

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Cell A1 | Cell B1 | Cell C1 |
| Cell A2 | Cell B2 | Cell C2 |

## Code Blocks

Fenced code blocks with language hints:

```python
def hello():
    print("Hello, world!")
```

Inline `code` is also styled distinctly.

## Lists

### Unordered
- Item one
- Item two
  - Nested item
  - Another nested

### Ordered
1. First
2. Second
3. Third

## Blockquotes

> This is a blockquote.
> 
> It can span multiple lines.

## Horizontal Rules

Three or more hyphens create a horizontal rule:

---

## Raw HTML

You can embed raw HTML directly:

<div class="custom-card" style="border: 1px solid #ccc; padding: 1rem; border-radius: 8px;">
    <strong>Custom Card</strong>
    <p>This HTML appears exactly as written.</p>
</div>

## Custom Frontmatter Fields

You can add any fields to frontmatter:

```yaml
---
title: "My Document"
author: "Your Name"
date: "2024-01-15"
version: "1.0.0"
---
```

Then access them in your template: `{{author}}`, `{{date}}`, etc.

## Using Custom Templates

```bash
renderkind input.md --template my-template.html
```

Your template must include the required placeholders: `{{title}}`, `{{description}}`, `{{content}}`, `{{toc}}`, `{{anchor_top}}`.

## Next Steps

- Read the [README](../README.md) for installation and usage
- Explore the `examples/` directory for more samples
- Customize the default template to match your branding
