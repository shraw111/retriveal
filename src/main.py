"""
Main Application - Drug Claims Retrieval System
Entry point for the complete pipeline (Phases 1-10)
"""
import asyncio
import logging
import sys
import os
import json
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .models.claim import ClaimsOutput
from .api.openfda import OpenFDAClient
from .api.pubmed import PubMedClient
from .api.clinicaltrials import ClinicalTrialsClient
from .utils.llm_client import ClaudeClient
from .processors.intent_parser import IntentParser
from .processors.search_orchestrator import SearchOrchestrator
from .processors.ranker import ResultsRanker
from .processors.claims_generator import ClaimsGenerator
from .utils.validators import SearchValidator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DrugClaimsRetrieval:
    """Main application orchestrator"""

    def __init__(self):
        """Initialize all components"""
        logger.info("Initializing Drug Claims Retrieval System")

        # Get API keys from environment
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment. "
                "Please set it in .env file or environment variables."
            )

        ncbi_api_key = os.getenv("NCBI_API_KEY")
        ncbi_email = os.getenv("NCBI_EMAIL")

        # Initialize API clients
        self.openfda = OpenFDAClient(timeout=30)
        self.pubmed = PubMedClient(
            api_key=ncbi_api_key,
            email=ncbi_email,
            timeout=30,
            max_results=int(os.getenv("MAX_RESULTS_PUBMED", "20"))
        )
        self.clinicaltrials = ClinicalTrialsClient(
            timeout=30,
            page_size=int(os.getenv("MAX_RESULTS_CLINICAL_TRIALS", "10"))
        )

        # Initialize LLM client
        self.claude = ClaudeClient(api_key=anthropic_api_key)

        # Initialize processors
        self.intent_parser = IntentParser(self.claude, self.openfda)
        self.search_orchestrator = SearchOrchestrator(
            self.openfda,
            self.pubmed,
            self.clinicaltrials
        )
        self.ranker = ResultsRanker(self.claude)
        self.claims_generator = ClaimsGenerator(self.claude)

        # Initialize validators
        self.search_validator = SearchValidator()

        logger.info("Initialization complete")

    async def process_query(self, user_query: str) -> ClaimsOutput:
        """
        Complete pipeline: Process user query and return claims

        Phases:
        1. Intent extraction
        2-4. Parallel search
        5. Ranking
        6-8. Claims generation
        9. Quality assurance

        Args:
            user_query: Free-text user query

        Returns:
            ClaimsOutput with all claims and metadata
        """
        pipeline_start = time.time()

        try:
            # PHASE 1: Intent Extraction
            logger.info("=" * 80)
            logger.info("PHASE 1: Intent Extraction")
            logger.info("=" * 80)
            user_intent = await self.intent_parser.parse(user_query)
            logger.info(f"Intent: {user_intent.claim_type} claims for "
                       f"{user_intent.drug.brand_name or user_intent.drug.generic_name}")

            # PHASE 2-4: Parallel Search
            logger.info("=" * 80)
            logger.info("PHASE 2-4: Parallel Search Execution")
            logger.info("=" * 80)
            search_start = time.time()
            search_results = await self.search_orchestrator.search_all_sources(user_intent)
            search_time = time.time() - search_start
            logger.info(f"Search completed in {search_time:.2f} seconds")

            # Validate search results
            is_valid, warnings = self.search_validator.validate_search_results(
                search_results.model_dump()
            )
            if not is_valid:
                logger.error(f"Search validation failed: {warnings}")
                raise ValueError(f"No usable results found: {warnings}")

            for warning in warnings:
                logger.warning(warning)

            # PHASE 5: Filter and Rank
            logger.info("=" * 80)
            logger.info("PHASE 5: Results Filtering and Ranking")
            logger.info("=" * 80)

            # Filter for full text only
            filtered_results = self.ranker.filter_full_text_only(search_results)

            # Get excluded articles
            excluded_articles = self.ranker.get_excluded_articles(search_results)

            # Rank full-text articles by relevance
            if filtered_results.pubmed_full_text:
                ranked_articles = await self.ranker.rank_articles(
                    filtered_results.pubmed_full_text,
                    user_intent
                )
                logger.info(f"Ranked {len(ranked_articles)} full-text articles")
            else:
                ranked_articles = []
                logger.warning("No full-text articles available for ranking")

            # PHASE 6-8: Claims Generation
            logger.info("=" * 80)
            logger.info("PHASE 6-8: Claims Generation")
            logger.info("=" * 80)

            claims_output = await self.claims_generator.generate_claims(
                search_results=filtered_results,
                ranked_articles=ranked_articles,
                clinical_trials=filtered_results.clinical_trials,
                user_intent=user_intent,
                search_time=search_time,
                excluded_articles=excluded_articles
            )

            # PHASE 9: Quality Assurance (already integrated in claims generation)
            logger.info("=" * 80)
            logger.info("PHASE 9: Quality Assurance Complete")
            logger.info("=" * 80)
            logger.info(f"Generated {len(claims_output.claims)} validated claims")

            pipeline_time = time.time() - pipeline_start
            logger.info("=" * 80)
            logger.info(f"PIPELINE COMPLETE - Total time: {pipeline_time:.2f} seconds")
            logger.info("=" * 80)

            return claims_output

        except Exception as e:
            logger.error(f"Error in pipeline: {e}", exc_info=True)
            raise

    async def process_and_save(
        self,
        user_query: str,
        output_file: Optional[str] = None
    ) -> str:
        """
        Process query and save results to JSON file

        Args:
            user_query: User query
            output_file: Output file path (optional)

        Returns:
            Path to output file
        """
        # Process query
        claims_output = await self.process_query(user_query)

        # Determine output file path
        if not output_file:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"claims_{timestamp}.json"
        else:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)

        # Save to file
        with open(output_file, "w") as f:
            json.dump(
                claims_output.model_dump(mode="json"),
                f,
                indent=2,
                default=str
            )

        logger.info(f"Results saved to: {output_file}")
        return str(output_file)


async def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <user_query> [output_file]")
        print("\nExample:")
        print('  python -m src.main "efficacy claims for Paxlovid in COVID-19"')
        print('  python -m src.main "safety claims for Keytruda in melanoma" output.json')
        sys.exit(1)

    user_query = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Initialize system
    system = DrugClaimsRetrieval()

    # Process query
    try:
        output_path = await system.process_and_save(user_query, output_file)
        print(f"\n{'=' * 80}")
        print("SUCCESS!")
        print(f"{'=' * 80}")
        print(f"Claims generated and saved to: {output_path}")
        print("\nTo view results:")
        print(f"  cat {output_path}")
        print(f"  python -m json.tool {output_path}")

    except Exception as e:
        print(f"\n{'=' * 80}")
        print("ERROR!")
        print(f"{'=' * 80}")
        print(f"Failed to process query: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
