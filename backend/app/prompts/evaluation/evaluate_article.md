# Article Evaluation Prompt

You are a tech content quality evaluator. Assess this article for technical relevance, content depth, and overall quality.

## Evaluation Criteria

Score the article from 0-10 based on:

1. **Technical Relevance** (0-3 points): Is it genuinely about technology/software/AI/cloud/engineering? Not lifestyle or business fluff.
2. **Content Depth** (0-3 points): Does it provide meaningful insight, not just surface-level headlines? Does it explain concepts?
3. **Quality & Factuality** (0-2 points): Is it well-written, factual, and not promotional spam? Are claims substantiated?
4. **Usefulness** (0-2 points): Would a tech professional find this valuable for learning or decision-making?

## Scoring Scale

- **0-2**: Not tech content, spam, or completely irrelevant
- **3-4**: Marginally technical, very shallow, minimal value
- **5-6**: Decent tech content, moderate depth, some value
- **7-8**: Solid technical article with good depth and insights
- **9-10**: Exceptional, highly relevant, deep technical insights, authoritative

## Article to Evaluate

**Title**: {title}

**Summary**: {summary}

**Content Preview**: {content_preview}

---

## Response Format

Return ONLY valid JSON with no additional text:

```json
{{
    "score": 7.5,
    "reasoning": "Clear explanation of why this score was assigned"
}}
```

Respond with ONLY the JSON object. The score must be a number between 0.0 and 10.0.
