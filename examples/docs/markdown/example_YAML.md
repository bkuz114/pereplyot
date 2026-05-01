---
title: "Dummy Markdown File with Rich Features"
description: "This file demonstrates basic and advanced Markdown capabilities, including lists, tables, code blocks, HTML, and YAML frontmatter."
type: github
---

# Heading Level 1: Document Title

## Heading Level 2: Introduction

This is a paragraph with **bold**, *italic*, and `inline code` text. You can also use ~~strikethrough~~ and [a hyperlink](https://example.com).

### Heading Level 3: Lists

#### Unordered List
- First item
- Second item
  - Nested item 1
  - Nested item 2
- Third item

#### Ordered List
1. Step one
2. Step two
   1. Substep A
   2. Substep B
3. Step three

---

## Heading Level 2: Tables

| Feature       | Supported | Notes                      |
|---------------|-----------|----------------------------|
| Lists         | Yes       | Both ordered & unordered   |
| Tables        | Yes       | With alignment             |
| Code blocks   | Yes       | Inline and block           |
| HTML          | Yes       | Custom divs, styling       |
| Frontmatter   | Yes       | YAML metadata              |

---

## Heading Level 2: Code Blocks

Inline code example: `print("Hello, world!")`

Block code (Python):

```python
def greet(name):
    """Say hello."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("Markdown"))
```

Block code (JSON):

```json
{
  "title": "Dummy File",
  "features": ["lists", "tables", "code", "html"]
}
```

---

## Heading Level 2: Custom HTML

<div style="background-color: #f0f0f0; padding: 15px; border-left: 5px solid #007acc; margin: 20px 0;">
  <p style="font-family: Arial, sans-serif; color: #333;">
    This is a <strong>custom HTML div</strong> with inline styling.  
    You can use it for notes, warnings, or callout boxes.
  </p>
  <ul>
    <li>Works with nested HTML elements</li>
    <li>Supports <span style="color: red;">colored text</span> and backgrounds</li>
  </ul>
</div>

### Another HTML Example: Centered Box

<div align="center" style="border: 1px solid #ccc; border-radius: 8px; padding: 10px; width: 80%; margin: auto;">
  <h4>✨ Centered Content ✨</h4>
  <p>This box uses a mix of HTML and inline CSS.</p>
</div>

---

## Heading Level 3: Horizontal Rule and Final Notes

Here’s a horizontal rule:

***
