# Article Processing Prompt

You are a professional content editor and analyst. Process this article and generate ALL required metadata in a single JSON response.

## Article Content

{content}

{images_section}

## Instructions

1. Generate a clear, engaging title (5-12 words) if not provided. Use the provided title if it exists.
2. Write a 2-3 sentence summary capturing main points and key findings
3. Classify into 1-3 categories (most relevant first): {categories_str}
4. Rate technical quality and relevance on a scale of 0-10 where 10 = exceptional tech content, 0 = spam/irrelevant
5. Generate 4-6 semantic tags (single words or short phrases, lowercase, hyphen-separated)
6. Structure article as DETAILED markdown with comprehensive sections (2000-3000 chars) - include key points, explanations, examples, important details. Use proper markdown formatting with headers, lists, and clear structure
7. Embed 2-3 most relevant images only (contextually throughout content)

## Context

- PROVIDED TITLE: {title}
- PROVIDED AUTHOR: {author}

## Categories (choose 1-3, in order of relevance)

{categories_str}

## Critical JSON Response Format

Return ONLY a valid JSON object (no markdown code blocks, no extra text before/after)

```json
{{
    "title": "Clear, engaging title under 100 chars",
    "summary": "2-3 sentence summary of main points",
    "categories": ["Primary", "Secondary"],
    "quality_score": 8.5,
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "markdown_content": "Detailed markdown content with sections, headers, lists, and embedded images using ![description](url) format"
}}
```

## Important Requirements

- **Title**: under 100 characters, engaging
- **Summary**: exactly 2-3 sentences
- **Categories**: choose 1-3 from the list above, in order of importance
- **Quality Score**: 0-10 float value based on tech relevance and content depth
- **Tags**: 4-6 lowercase tags, hyphen-separated, no special chars
- **Markdown**: DETAILED formatting with comprehensive content (2000-3000 chars) - include explanations, examples, and important details. Proper headers, sections, lists, and clear structure. This is the main article content
- **Images**: embed as ![description](url) contextually throughout content
- **NO title or author in markdown_content**, just body with embedded images
- **MUST return ONLY valid JSON** - nothing else!
- **Escape special characters**: Use \\n for newlines, \\" for quotes in string values
