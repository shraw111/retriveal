"""
Search Orchestrator - Phases 2-4: Parallel Search Strategy & Execution
Coordinates parallel searches across OpenFDA, PubMed/PMC, and ClinicalTrials.gov
"""
import asyncio
import logging
import time
from typing import Tuple

from ..models.intent import UserIntent
from ..models.api_responses import (
    SearchResults,
    FDALabelResponse,
    PubMedArticleMetadata,
    PubMedFullTextArticle,
    ClinicalTrialResult
)
from ..api.openfda import OpenFDAClient
from ..api.pubmed import PubMedClient
from ..api.clinicaltrials import ClinicalTrialsClient

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """Orchestrates parallel searches across all 3 data sources"""

    def __init__(
        self,
        openfda_client: OpenFDAClient,
        pubmed_client: PubMedClient,
        clinicaltrials_client: ClinicalTrialsClient
    ):
        """
        Initialize search orchestrator

        Args:
            openfda_client: OpenFDA API client
            pubmed_client: PubMed/PMC API client
            clinicaltrials_client: ClinicalTrials.gov API client
        """
        self.openfda = openfda_client
        self.pubmed = pubmed_client
        self.clinicaltrials = clinicaltrials_client

    async def search_all_sources(self, user_intent: UserIntent) -> SearchResults:
        """
        Execute parallel searches across all 3 sources

        This method runs all searches concurrently for maximum speed.
        Target: 8-12 seconds total execution time

        Args:
            user_intent: Structured user intent

        Returns:
            SearchResults with aggregated data from all sources
        """
        start_time = time.time()

        logger.info("Starting parallel search across all sources")
        logger.info(f"Drug: {user_intent.drug.brand_name or user_intent.drug.generic_name}")
        logger.info(f"Indication: {user_intent.indication}")
        logger.info(f"Population: {user_intent.population}")

        # Launch all 3 searches in parallel using asyncio.gather
        results = await asyncio.gather(
            self._search_openfda(user_intent),
            self._search_pubmed(user_intent),
            self._search_clinicaltrials(user_intent),
            return_exceptions=True  # Don't fail if one source fails
        )

        # Unpack results
        fda_label = results[0] if not isinstance(results[0], Exception) else None
        pubmed_result = results[1] if not isinstance(results[1], Exception) else ([], [])
        clinical_trials = results[2] if not isinstance(results[2], Exception) else []

        # Handle exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source_names = ["OpenFDA", "PubMed", "ClinicalTrials.gov"]
                logger.error(f"Error in {source_names[i]} search: {result}")

        # Unpack PubMed results
        all_pubmed_articles, pubmed_full_text = pubmed_result

        # Build SearchResults object
        search_results = SearchResults(
            fda_label=fda_label,
            pubmed_articles=all_pubmed_articles,
            pubmed_full_text=pubmed_full_text,
            clinical_trials=clinical_trials,
            pubmed_total_found=len(all_pubmed_articles),
            pubmed_full_text_available=len(pubmed_full_text),
            pubmed_abstract_only=len(all_pubmed_articles) - len(pubmed_full_text),
            clinical_trials_found=len(clinical_trials)
        )

        elapsed = time.time() - start_time
        logger.info(f"Parallel search completed in {elapsed:.2f} seconds")
        logger.info(f"Results: FDA={fda_label is not None}, "
                   f"PubMed={len(all_pubmed_articles)} ({len(pubmed_full_text)} full text), "
                   f"Trials={len(clinical_trials)}")

        return search_results

    async def _search_openfda(self, user_intent: UserIntent) -> FDALabelResponse:
        """
        Search OpenFDA for drug label

        Args:
            user_intent: User intent with drug info

        Returns:
            FDALabelResponse or None
        """
        logger.info("Searching OpenFDA...")

        try:
            result = await self.openfda.search(
                brand_name=user_intent.drug.brand_name,
                generic_name=user_intent.drug.generic_name
            )
            return result
        except Exception as e:
            logger.error(f"OpenFDA search failed: {e}")
            raise

    async def _search_pubmed(
        self,
        user_intent: UserIntent
    ) -> Tuple[list[PubMedArticleMetadata], list[PubMedFullTextArticle]]:
        """
        Search PubMed/PMC with 3-step process

        Steps:
        1. Search for PMIDs
        2. Get metadata (find PMC IDs)
        3. Fetch full text from PMC

        Args:
            user_intent: User intent

        Returns:
            Tuple of (all articles metadata, full text articles only)
        """
        logger.info("Searching PubMed/PMC (3-step process)...")

        try:
            # Determine primary search term
            drug_name = user_intent.drug.brand_name or user_intent.drug.generic_name
            if not drug_name:
                logger.warning("No drug name available for PubMed search")
                return [], []

            # Execute 3-step workflow
            all_articles, full_text_articles = await self.pubmed.search_and_get_full_text(
                drug_name=drug_name,
                indication=user_intent.indication,
                population=user_intent.population
            )

            return all_articles, full_text_articles

        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            raise

    async def _search_clinicaltrials(
        self,
        user_intent: UserIntent
    ) -> list[ClinicalTrialResult]:
        """
        Search ClinicalTrials.gov

        Args:
            user_intent: User intent

        Returns:
            List of ClinicalTrialResult
        """
        logger.info("Searching ClinicalTrials.gov...")

        try:
            drug_name = user_intent.drug.brand_name or user_intent.drug.generic_name
            if not drug_name:
                logger.warning("No drug name available for ClinicalTrials search")
                return []

            results = await self.clinicaltrials.search_trials(
                drug_name=drug_name,
                indication=user_intent.indication,
                phase="PHASE3",  # Focus on Phase 3 trials
                status="COMPLETED"  # Only completed trials
            )

            return results

        except Exception as e:
            logger.error(f"ClinicalTrials.gov search failed: {e}")
            raise
