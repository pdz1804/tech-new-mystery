"""Utility to load LLM prompts from markdown files."""

import os
import logging

logger = logging.getLogger(__name__)

# Prompts directory is at app/prompts/
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


def load_prompt(path: str) -> str:
    """Load a prompt template from app/prompts/ directory.

    Args:
        path: Relative path under prompts/ (e.g., 'evaluation/evaluate_article.md')

    Returns:
        Prompt content as string

    Raises:
        FileNotFoundError: If prompt file not found
    """
    full_path = os.path.normpath(os.path.join(_PROMPTS_DIR, path))

    # Security: ensure path doesn't escape prompts dir
    real_prompts_dir = os.path.realpath(_PROMPTS_DIR)
    real_full_path = os.path.realpath(full_path)
    if not real_full_path.startswith(real_prompts_dir):
        raise ValueError(f"Invalid prompt path: {path}")

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.debug(f"Loaded prompt from {path} ({len(content)} chars)")
        return content
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {full_path}")
        raise
