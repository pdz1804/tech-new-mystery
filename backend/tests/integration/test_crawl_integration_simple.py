"""Simplified end-to-end test for Crawl4AI integration."""

import asyncio
import json
import time
from datetime import datetime

from app.services.scraping_service import ScrapingService
from app.services.article_processing_service import ArticleProcessingService


class SimpleTestRunner:
    """Simple test runner for Crawl4AI integration."""

    def __init__(self):
        self.scraper = ScrapingService()
        self.processor = ArticleProcessingService()
        self.results = {
            "tests": [],
            "metrics": {},
            "samples": [],
            "summary": {
                "passed": 0,
                "failed": 0,
                "total": 0,
                "timestamp": datetime.now().isoformat()
            }
        }

    async def test_installation(self):
        """Test 1: Verify Crawl4AI is installed."""
        print("\n[TEST 1] Verifying Crawl4AI Installation")
        print("-" * 80)

        try:
            from crawl4ai import AsyncWebCrawler
            print("[PASS] Crawl4AI import successful")
            self.results["tests"].append({"name": "Installation", "passed": True})
            self.results["summary"]["passed"] += 1
            return True
        except Exception as e:
            print("[FAIL] Crawl4AI import failed: %s" % str(e))
            self.results["tests"].append({"name": "Installation", "passed": False, "error": str(e)})
            self.results["summary"]["failed"] += 1
            return False

    async def test_scraping_with_mock(self):
        """Test 2: Test scraping with mock content."""
        print("\n[TEST 2] Testing Markdown Extraction Quality")
        print("-" * 80)

        # Test with mock HTML content to verify markdown extraction logic
        test_html = """
        <html>
        <head><title>Test Article</title></head>
        <body>
            <h1>Breaking: AI Reaches New Milestone</h1>
            <p>New research shows significant progress in artificial intelligence.</p>
            <p>Machine learning models are improving rapidly.</p>
            <p>Future applications span healthcare, finance, and more.</p>
            <script>console.log('hidden');</script>
            <style>.hidden { display: none; }</style>
        </body>
        </html>
        """

        try:
            # Test markdown extraction from HTML
            result = await self.processor.process_url_content(
                url="https://example.com/test",
                raw_content=test_html,
                title="Test Article",
                author="Test Bot"
            )

            checks = {
                "title_ok": result.get("title") is not None,
                "author_ok": result.get("author") == "Test Bot",
                "markdown_ok": result.get("structured_markdown") is not None,
                "summary_ok": result.get("summary") is not None,
                "category_ok": result.get("category") in self.processor.CATEGORIES,
                "tags_ok": len(result.get("tags", [])) > 0,
            }

            for check, passed in checks.items():
                status = "[PASS]" if passed else "[FAIL]"
                print("  %s %s" % (status, check))

            all_passed = all(checks.values())

            if all_passed:
                print("[PASS] Markdown extraction quality verified")
                self.results["tests"].append({"name": "Markdown Extraction", "passed": True})
                self.results["summary"]["passed"] += 1

                # Store sample
                self.results["samples"].append({
                    "url": "https://example.com/test",
                    "title": result.get("title"),
                    "category": result.get("category"),
                    "tags": result.get("tags"),
                    "summary": result.get("summary")[:100] if result.get("summary") else None
                })
            else:
                print("[FAIL] Some markdown extraction checks failed")
                self.results["tests"].append({"name": "Markdown Extraction", "passed": False})
                self.results["summary"]["failed"] += 1

            return all_passed

        except Exception as e:
            print("[FAIL] Markdown extraction test failed: %s" % str(e))
            self.results["tests"].append({"name": "Markdown Extraction", "passed": False, "error": str(e)})
            self.results["summary"]["failed"] += 1
            return False

    async def test_llm_processing(self):
        """Test 3: Test LLM processing pipeline."""
        print("\n[TEST 3] Testing LLM Processing Pipeline")
        print("-" * 80)

        test_content = """
        <html>
        <body>
            <h1>Quantum Computing Breakthrough 2024</h1>
            <p>Scientists announce breakthrough in quantum computing error correction.</p>
            <p>The new approach reduces error rates by 50 percent, a major milestone.</p>
            <p>Companies like IBM, Google, and others are racing to commercialize the technology.</p>
            <p>Applications in drug discovery, materials science, and optimization problems are expected soon.</p>
            <p>However, fully practical quantum computers are still years away.</p>
        </body>
        </html>
        """

        start_time = time.time()
        try:
            result = await self.processor.process_url_content(
                url="https://example.com/quantum",
                raw_content=test_content,
                title=None,
                author="Science Writer"
            )
            elapsed = time.time() - start_time

            checks = {
                "title_generated": result.get("title") and result["title"] != "Untitled",
                "summary_generated": result.get("summary") is not None,
                "category_valid": result.get("category") in self.processor.CATEGORIES,
                "tags_count": len(result.get("tags", [])) >= 3,
                "markdown_generated": result.get("structured_markdown") is not None,
                "processing_time": elapsed < 30,
            }

            for check, passed in checks.items():
                status = "[PASS]" if passed else "[FAIL]"
                value = ""
                if check == "title_generated" and passed:
                    value = " - %s" % result.get("title")[:50]
                elif check == "category_valid" and passed:
                    value = " - %s" % result.get("category")
                elif check == "tags_count" and passed:
                    value = " - %d tags" % len(result.get("tags", []))
                elif check == "processing_time" and passed:
                    value = " - %.2f seconds" % elapsed
                print("  %s %s%s" % (status, check, value))

            all_passed = all(checks.values())

            if all_passed:
                print("[PASS] LLM processing pipeline verified")
                self.results["tests"].append({"name": "LLM Processing", "passed": True})
                self.results["metrics"]["llm_processing_time"] = {"value": elapsed, "unit": "seconds"}
                self.results["summary"]["passed"] += 1
            else:
                print("[FAIL] Some LLM processing checks failed")
                self.results["tests"].append({"name": "LLM Processing", "passed": False})
                self.results["summary"]["failed"] += 1

            return all_passed

        except Exception as e:
            elapsed = time.time() - start_time
            print("[FAIL] LLM processing test failed: %s" % str(e))
            self.results["tests"].append({"name": "LLM Processing", "passed": False, "error": str(e)})
            self.results["summary"]["failed"] += 1
            return False

    async def test_error_handling(self):
        """Test 4: Test error handling."""
        print("\n[TEST 4] Testing Error Handling")
        print("-" * 80)

        all_passed = True

        # Test empty URL
        result = await self.scraper.scrape_url("")
        empty_ok = not result["success"]
        status = "[PASS]" if empty_ok else "[FAIL]"
        print("  %s Empty URL rejected" % status)
        all_passed = all_passed and empty_ok

        # Test PDF URL
        result = await self.scraper.scrape_url("https://example.com/file.pdf")
        pdf_ok = not result["success"] and "PDF" in result["error"]
        status = "[PASS]" if pdf_ok else "[FAIL]"
        print("  %s PDF URL rejected" % status)
        all_passed = all_passed and pdf_ok

        # Test short content
        result = await self.processor.process_url_content(
            url="https://example.com/short",
            raw_content="short",
            title="Test"
        )
        short_ok = result["summary"] is None
        status = "[PASS]" if short_ok else "[FAIL]"
        print("  %s Short content handled" % status)
        all_passed = all_passed and short_ok

        if all_passed:
            print("[PASS] Error handling verified")
            self.results["tests"].append({"name": "Error Handling", "passed": True})
            self.results["summary"]["passed"] += 1
        else:
            print("[FAIL] Some error handling checks failed")
            self.results["tests"].append({"name": "Error Handling", "passed": False})
            self.results["summary"]["failed"] += 1

        return all_passed

    async def test_quality_checks(self):
        """Test 5: Quality and performance checks."""
        print("\n[TEST 5] Quality Metrics")
        print("-" * 80)

        passed = self.results["summary"]["passed"]
        failed = self.results["summary"]["failed"]
        total = passed + failed

        print("Total tests: %d" % total)
        print("Passed: %d" % passed)
        print("Failed: %d" % failed)

        if total > 0:
            success_rate = (passed / total) * 100
        else:
            success_rate = 0

        print("Success rate: %.1f%%" % success_rate)

        quality_ok = success_rate >= 75
        status = "[PASS]" if quality_ok else "[FAIL]"
        print("%s Overall quality threshold met" % status)

        self.results["tests"].append({"name": "Quality Metrics", "passed": quality_ok})
        if quality_ok:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1

        return quality_ok

    async def run_all(self):
        """Run all tests."""
        print("\n" + "=" * 80)
        print("CRAWL4AI INTEGRATION TEST SUITE")
        print("=" * 80)

        await self.test_installation()
        await self.test_scraping_with_mock()
        await self.test_llm_processing()
        await self.test_error_handling()
        await self.test_quality_checks()

        return self.results


async def main():
    """Main entry point."""
    runner = SimpleTestRunner()
    results = await runner.run_all()

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("Passed: %d" % results["summary"]["passed"])
    print("Failed: %d" % results["summary"]["failed"])
    print("Total: %d" % (results["summary"]["passed"] + results["summary"]["failed"]))

    success_rate = (results["summary"]["passed"] / (results["summary"]["passed"] + results["summary"]["failed"]) * 100) if (results["summary"]["passed"] + results["summary"]["failed"]) > 0 else 0
    print("Success Rate: %.1f%%" % success_rate)
    print("=" * 80)

    # Save results
    with open("CRAWL4AI_TEST_RESULTS.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to CRAWL4AI_TEST_RESULTS.json")

    # Print samples
    if results["samples"]:
        print("\n" + "=" * 80)
        print("SAMPLE DATA")
        print("=" * 80)
        for sample in results["samples"]:
            print("\nURL: %s" % sample["url"])
            print("Title: %s" % sample["title"])
            print("Category: %s" % sample["category"])
            print("Tags: %s" % ", ".join(sample["tags"]))
            if sample["summary"]:
                print("Summary: %s..." % sample["summary"])

    return 0 if results["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
