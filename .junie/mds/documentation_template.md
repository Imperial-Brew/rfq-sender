# docs/documentation_template.md

This is a standardized template for documentation in the RFQ Sender project. All documentation files should follow this format to ensure consistency across the project.

## Format Guidelines

### Headings

- Use H1 (`#`) only for the top-level heading, which should include the file path
- Use H2 (`##`) for major sections
- Use H3 (`###`) for subsections
- Use H4 (`####`) for sub-subsections if needed

### Code Blocks

Always use triple backticks with a language identifier:

```python
def example_function():
    """Example docstring."""
    return "This is an example function"
```

```bash
# Example bash command
pip install -r requirements.txt
```

### Lists

For unordered lists:
- Use hyphen (`-`) for list items
- Indent with 2 spaces for nested items
  - Like this
  - And this

For ordered lists:
1. Use numbers for ordered lists
2. Indent with 3 spaces for nested items
   1. Like this
   2. And this

### Task Lists

- [ ] Uncompleted task
- [x] Completed task

### Line Length

Keep lines to a maximum of 80 characters where possible. This improves readability, especially when viewing documentation in a terminal or side-by-side with code.

### Links

Use reference-style links for better readability:

[Link text][reference]

[reference]: https://example.com

For internal links to other documentation files, use relative paths:

[Another Document](another_document.md)

## Document Structure

### Required Sections

Every documentation file should include:

1. **Top-level heading with file path**
2. **Brief description** of the document's purpose
3. **Table of Contents** for longer documents
4. **Relevant sections** based on the document type
5. **Related Documents** section at the end

### Example Structure

```markdown
# docs/example_document.md

Brief description of what this document covers.

## Table of Contents
- [Section 1](#section-1)
- [Section 2](#section-2)
- [Section 3](#section-3)

## Section 1
Content for section 1.

## Section 2
Content for section 2.

## Section 3
Content for section 3.

## Related Documents
- [Document 1](document1.md)
- [Document 2](document2.md)
```

## Document Types

### User Guides

User guides should include:
- Purpose of the feature/tool
- Prerequisites
- Step-by-step instructions
- Examples
- Troubleshooting

### Technical Documentation

Technical documentation should include:
- Architecture overview
- Component descriptions
- API documentation
- Data flow diagrams
- Implementation details

### Implementation Summaries

Implementation summaries should include:
- Issue description
- Solution approach
- Changes made
- Testing performed
- Future considerations

## Best Practices

1. **Keep documentation up-to-date** with code changes
2. **Use clear, concise language**
3. **Include examples** where appropriate
4. **Add diagrams** for complex concepts
5. **Link to related documentation** to avoid duplication
6. **Update the Documentation Index** when adding new documentation