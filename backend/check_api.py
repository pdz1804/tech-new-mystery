#!/usr/bin/env python3
"""Check Crawl4AI 0.4.0 API."""

import asyncio
import inspect

try:
    from crawl4ai import AsyncWebCrawler

    # Check arun signature
    sig = inspect.signature(AsyncWebCrawler.arun)
    print("AsyncWebCrawler.arun parameters:")
    for param_name, param in sig.parameters.items():
        annotation = param.annotation if param.annotation != inspect.Parameter.empty else 'Any'
        default = param.default if param.default != inspect.Parameter.empty else 'required'
        print(f"  {param_name}: {annotation} = {default}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
