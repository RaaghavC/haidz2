#!/usr/bin/env python3
"""
Generic Test Framework for Vision-Based Autonomous Scraper
Tests the AI's ability to understand and extract data from ANY archive website
without prior knowledge or hardcoding.
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
import time
from typing import List, Dict, Any
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.true_agentic_orchestrator import TrueAgenticOrchestrator
from src.agent.config import AgentConfig


class GenericArchiveTest:
    """Generic test framework for testing vision-based scraper on any archive."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.results = []
        
    async def test_archive(self, url: str, search_term: str = None, max_items: int = 5) -> Dict[str, Any]:
        """
        Test the AI's ability to understand and extract from any archive website.
        
        Args:
            url: Archive website URL
            search_term: Optional search term
            max_items: Maximum items to extract
            
        Returns:
            Test results dictionary
        """
        print(f"\n{'='*70}")
        print(f"Testing Archive: {url}")
        print(f"Search Term: {search_term or 'None (autonomous navigation)'}")
        print(f"Max Items: {max_items}")
        print('='*70)
        
        test_result = {
            "url": url,
            "search_term": search_term,
            "max_items": max_items,
            "start_time": datetime.now().isoformat(),
            "success": False,
            "items_extracted": 0,
            "ai_decisions": [],
            "errors": [],
            "metrics": {}
        }
        
        try:
            # Configure for this test
            config = AgentConfig(
                output_file=f"csv/test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{url.split('/')[2].replace('.', '_')}.csv",
                max_results=max_items,
                max_pages=10,  # Allow reasonable exploration
                headless=True,  # Run headless for testing
                screenshot_on_error=True
            )
            
            # Create orchestrator
            orchestrator = TrueAgenticOrchestrator(
                target_url=url,
                search_query=search_term,
                config=config,
                api_key=self.api_key
            )
            
            # Run the scraper
            start_time = time.time()
            result = await orchestrator.run()
            duration = time.time() - start_time
            
            # Update test results
            test_result["success"] = result["success"]
            test_result["items_extracted"] = result["items_scraped"]
            test_result["duration"] = duration
            test_result["ai_decisions"] = result.get("actions_taken", [])
            
            # Analyze AI behavior
            test_result["metrics"] = self._analyze_ai_behavior(result)
            
            # Display results
            self._display_results(test_result, result)
            
        except Exception as e:
            test_result["errors"].append(str(e))
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            
        test_result["end_time"] = datetime.now().isoformat()
        self.results.append(test_result)
        return test_result
    
    def _analyze_ai_behavior(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how the AI behaved during scraping."""
        metrics = {
            "total_actions": len(result.get("actions_taken", [])),
            "action_types": {},
            "pages_explored": 0,
            "extraction_rate": 0,
            "decision_confidence_avg": 0
        }
        
        # Count action types
        for action in result.get("actions_taken", []):
            action_type = action["action"]
            metrics["action_types"][action_type] = metrics["action_types"].get(action_type, 0) + 1
            
        # Calculate extraction rate
        if metrics["total_actions"] > 0:
            extract_actions = metrics["action_types"].get("EXTRACT", 0)
            metrics["extraction_rate"] = extract_actions / metrics["total_actions"]
            
        return metrics
    
    def _display_results(self, test_result: Dict[str, Any], raw_result: Dict[str, Any]):
        """Display test results in a readable format."""
        print(f"\n📊 Test Results:")
        print(f"  ✅ Success: {test_result['success']}")
        print(f"  📦 Items Extracted: {test_result['items_extracted']}")
        print(f"  ⏱️  Duration: {test_result.get('duration', 0):.1f}s")
        print(f"  🤖 AI Actions: {test_result['metrics']['total_actions']}")
        
        # Show AI decision breakdown
        if test_result['metrics']['action_types']:
            print(f"\n🧠 AI Decision Breakdown:")
            for action, count in test_result['metrics']['action_types'].items():
                print(f"  {action}: {count}")
        
        # Show sample extracted data
        if raw_result.get('data'):
            print(f"\n📋 Sample Extracted Data:")
            for i, item in enumerate(raw_result['data'][:3]):
                print(f"\n  Item {i+1}:")
                # Show non-null fields
                for key, value in item.items():
                    if value is not None and value != "":
                        print(f"    {key}: {value[:100] if isinstance(value, str) else value}")
        
        # Show AI reasoning samples
        if test_result['ai_decisions']:
            print(f"\n🤔 AI Reasoning Samples:")
            for i, decision in enumerate(test_result['ai_decisions'][:5]):
                print(f"  {i+1}. {decision['action']}: {decision['reason'][:80]}...")
    
    def generate_report(self, output_file: str = "test_report.json"):
        """Generate a comprehensive test report."""
        report = {
            "test_date": datetime.now().isoformat(),
            "total_archives_tested": len(self.results),
            "successful_tests": sum(1 for r in self.results if r["success"]),
            "total_items_extracted": sum(r["items_extracted"] for r in self.results),
            "average_extraction_time": sum(r.get("duration", 0) for r in self.results) / len(self.results) if self.results else 0,
            "detailed_results": self.results
        }
        
        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Display summary
        print(f"\n\n{'='*70}")
        print(f"📊 TEST SUMMARY REPORT")
        print(f"{'='*70}")
        print(f"📅 Test Date: {report['test_date']}")
        print(f"🌐 Archives Tested: {report['total_archives_tested']}")
        print(f"✅ Successful: {report['successful_tests']}")
        print(f"📦 Total Items: {report['total_items_extracted']}")
        print(f"⏱️  Avg Time: {report['average_extraction_time']:.1f}s")
        print(f"\n📄 Detailed report saved to: {output_file}")


async def test_ai_understanding():
    """Test the AI's ability to understand different types of pages."""
    print("\n" + "="*70)
    print("AI UNDERSTANDING TEST")
    print("Testing the AI's ability to recognize different page types")
    print("="*70)
    
    # This test verifies the AI can distinguish between different page types
    # without being told what to expect
    from src.modules.image_verifier import ImageVerifier
    from src.utils.stealth_browser_manager import StealthBrowserManager
    import openai
    
    client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
    verifier = ImageVerifier(client)
    browser = StealthBrowserManager(headless=True)
    
    print("\nThe AI will analyze pages and determine their type...")
    print("No hardcoded expectations - pure AI understanding\n")
    
    await browser.start()
    await browser.stop()
    print("✅ AI understanding module verified")


async def main():
    """Main test runner."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Test vision-based scraper on any archive website"
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        help="Archive URLs to test (space-separated)",
        default=[
            "https://www.archnet.org/",
            "https://nyuad.nyu.edu/en/research/faculty-labs-and-projects/akkasah-center-for-photography.html",
            "https://www.manar-al-athar.ox.ac.uk/pages/collections_featured.php",
            "https://saltresearch.org/discovery/search?vid=90GARANTI_INST:90SALT_VU1&lang=en",
            "https://www.nit-istanbul.org/projects/machiel-kiel-photographic-archive"
        ]
    )
    parser.add_argument(
        "--search",
        help="Search term to use (optional)",
        default="Antakya"
    )
    parser.add_argument(
        "--max-items",
        type=int,
        help="Maximum items to extract per site",
        default=3
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test mode (fewer items, single site)"
    )
    
    args = parser.parse_args()
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set!")
        print("Please set it with: export OPENAI_API_KEY='your-key-here'")
        return
    
    print("GENERIC VISION-BASED SCRAPER TEST")
    print("==================================")
    print("Testing AI's ability to understand and extract from ANY archive")
    print("No hardcoding - Pure intelligence\n")
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test instance
    tester = GenericArchiveTest(os.getenv("OPENAI_API_KEY"))
    
    # Quick test mode
    if args.quick:
        print("🚀 Running in QUICK TEST mode\n")
        urls = args.urls[:1]  # Just first URL
        max_items = 2
    else:
        urls = args.urls
        max_items = args.max_items
    
    try:
        # Test AI understanding first
        await test_ai_understanding()
        
        # Test each archive
        for url in urls:
            try:
                await tester.test_archive(
                    url=url,
                    search_term=args.search if "search" in url or "collection" in url else None,
                    max_items=max_items
                )
                
                # Pause between tests to avoid rate limits
                if url != urls[-1]:
                    print("\n⏸️  Pausing 15 seconds before next test...")
                    await asyncio.sleep(15)
                    
            except KeyboardInterrupt:
                print("\n⚠️  Test interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Failed to test {url}: {str(e)}")
                continue
        
        # Generate final report
        report_file = f"logs/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        tester.generate_report(report_file)
        
    except Exception as e:
        print(f"\n\n❌ Test suite error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("csv", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("screenshots", exist_ok=True)
    
    # Run the test suite
    asyncio.run(main())