"""
Intent Parser - Phase 1: Input Processing & Intent Extraction
Transforms free-text queries into structured intent objects
"""
import logging
from typing import Optional

from ..models.intent import UserIntent, DrugIdentification, OutputRequirements
from ..utils.llm_client import ClaudeClient
from ..api.openfda import OpenFDAClient

logger = logging.getLogger(__name__)


class IntentParser:
    """Parses user queries into structured intent"""

    def __init__(self, claude_client: ClaudeClient, openfda_client: OpenFDAClient):
        """
        Initialize intent parser

        Args:
            claude_client: Claude API client for LLM processing
            openfda_client: OpenFDA client for drug name validation
        """
        self.claude = claude_client
        self.openfda = openfda_client

    async def parse(self, user_query: str) -> UserIntent:
        """
        Parse free-text query into structured UserIntent

        Args:
            user_query: User's free-text query

        Returns:
            UserIntent object with extracted information

        Example:
            >>> parser = IntentParser(claude, openfda)
            >>> intent = await parser.parse("efficacy claims for Paxlovid in COVID-19")
            >>> print(intent.drug.brand_name)  # "Paxlovid"
            >>> print(intent.claim_type)  # "efficacy"
        """
        logger.info(f"Parsing user query: {user_query}")

        # Step 1: Use LLM to extract initial intent
        intent_data = await self.claude.extract_intent(user_query)

        # Step 2: Validate and enrich drug information via OpenFDA
        drug_data = intent_data.get("drug", {})
        drug_info = await self._validate_and_enrich_drug(drug_data)

        # Step 3: Build structured intent object
        user_intent = UserIntent(
            original_query=user_query,
            drug=drug_info,
            claim_type=intent_data.get("claim_type", "efficacy"),
            indication=intent_data.get("indication"),
            population=intent_data.get("population"),
            output_requirements=OutputRequirements(**intent_data.get("output_requirements", {}))
        )

        logger.info(f"Parsed intent: {user_intent.model_dump_json(indent=2)}")
        return user_intent

    async def _validate_and_enrich_drug(self, drug_data: dict) -> DrugIdentification:
        """
        Validate drug name and enrich with FDA data

        Args:
            drug_data: Extracted drug information from LLM

        Returns:
            DrugIdentification with validated and enriched data
        """
        brand_name = drug_data.get("brand_name")
        generic_name = drug_data.get("generic_name")
        search_terms = drug_data.get("search_terms", [])

        # If we have a brand name, try to get generic name from OpenFDA
        if brand_name and not generic_name:
            logger.info(f"Looking up generic name for brand: {brand_name}")
            try:
                fda_label = await self.openfda.search_by_brand_name(brand_name)
                if fda_label and fda_label.generic_name:
                    generic_name = fda_label.generic_name
                    logger.info(f"Found generic name: {generic_name}")

                    # Add to search terms if not already present
                    if generic_name and generic_name not in search_terms:
                        search_terms.append(generic_name)
            except Exception as e:
                logger.warning(f"Could not look up drug in OpenFDA: {e}")

        # Ensure brand and generic names are in search terms
        if brand_name and brand_name not in search_terms:
            search_terms.insert(0, brand_name)
        if generic_name and generic_name not in search_terms:
            search_terms.append(generic_name)

        # Build synonyms list (for now, same as search terms)
        synonyms = [term for term in search_terms if term not in [brand_name, generic_name]]

        return DrugIdentification(
            brand_name=brand_name,
            generic_name=generic_name,
            synonyms=synonyms,
            search_terms=search_terms
        )
