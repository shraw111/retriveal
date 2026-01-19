"""
Example: How to use the Drug Claims Retrieval System

This example demonstrates:
1. Basic query processing
2. Accessing results
3. Formatting output
"""
import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import DrugClaimsRetrieval


async def example_basic_query():
    """Example 1: Basic query"""
    print("=" * 80)
    print("EXAMPLE 1: Basic Query")
    print("=" * 80)

    # Initialize system
    system = DrugClaimsRetrieval()

    # Query
    query = "efficacy claims for Paxlovid in treating COVID-19 in high-risk patients"

    print(f"\nQuery: {query}\n")

    # Process
    result = await system.process_query(query)

    # Display summary
    print("\nSEARCH SUMMARY:")
    print(f"  Sources searched: {', '.join(result.search_summary.sources_searched)}")
    print(f"  Search time: {result.search_summary.search_time_seconds:.2f} seconds")
    print(f"\nRESULTS FOUND:")
    for source, count in result.search_summary.results_found.items():
        print(f"  {source}: {count}")

    print(f"\nCLAIMS GENERATED: {len(result.claims)}")

    # Display first claim
    if result.claims:
        claim = result.claims[0]
        print(f"\n{'=' * 80}")
        print(f"CLAIM #{claim.claim_id}")
        print(f"{'=' * 80}")
        print(f"Type: {claim.claim_type}")
        print(f"Source: {claim.source_type}")
        print(f"Confidence: {claim.confidence}")
        print(f"\nClaim Text:")
        print(f"  {claim.claim_text}")
        print(f"\nSubstantiation:")
        print(f"  {claim.substantiation[:300]}...")
        print(f"\nCitations: {len(claim.citations)}")
        for i, citation in enumerate(claim.citations, 1):
            print(f"  [{i}] {citation.citation_type} (Primary: {citation.primary})")

    # Display excluded articles
    excluded = result.additional_context.get("articles_without_full_text", [])
    if excluded:
        print(f"\n{'=' * 80}")
        print(f"EXCLUDED ARTICLES (No Full Text): {len(excluded)}")
        print(f"{'=' * 80}")
        for article in excluded[:3]:  # Show first 3
            print(f"\n  PMID: {article.pmid}")
            print(f"  Title: {article.title[:80]}...")
            print(f"  Journal: {article.journal}")
            print(f"  Note: {article.note}")


async def example_save_to_file():
    """Example 2: Save results to file"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Save Results to File")
    print("=" * 80)

    system = DrugClaimsRetrieval()
    query = "safety claims for Keytruda in melanoma"

    print(f"\nQuery: {query}")

    # Process and save
    output_file = await system.process_and_save(
        query,
        output_file="examples/output/keytruda_claims.json"
    )

    print(f"\nResults saved to: {output_file}")

    # Read and display summary
    with open(output_file) as f:
        data = json.load(f)

    print(f"\nGenerated {len(data['claims'])} claims")
    print(f"File size: {Path(output_file).stat().st_size} bytes")


async def example_multiple_queries():
    """Example 3: Process multiple queries"""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Multiple Queries")
    print("=" * 80)

    system = DrugClaimsRetrieval()

    queries = [
        "efficacy claims for Humira in rheumatoid arthritis",
        "safety profile for Ozempic in type 2 diabetes",
        "dosing information for Eliquis in atrial fibrillation"
    ]

    results = []
    for query in queries:
        print(f"\nProcessing: {query}")
        result = await system.process_query(query)
        results.append({
            "query": query,
            "claims_count": len(result.claims),
            "search_time": result.search_summary.search_time_seconds
        })

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for r in results:
        print(f"\nQuery: {r['query']}")
        print(f"  Claims: {r['claims_count']}")
        print(f"  Time: {r['search_time']:.2f}s")


async def main():
    """Run all examples"""
    try:
        # Example 1: Basic query
        await example_basic_query()

        # Example 2: Save to file
        # await example_save_to_file()

        # Example 3: Multiple queries (commented out - takes time)
        # await example_multiple_queries()

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
