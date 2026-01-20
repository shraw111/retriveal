"""
Claims Generator - Phases 6-8: Claims Generation, Citation Formatting, Output Generation
Generates MLR-ready claims from full-text articles and FDA labels
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.intent import UserIntent
from ..models.api_responses import (
    SearchResults,
    FDALabelResponse,
    PubMedFullTextArticle,
    ClinicalTrialResult
)
from ..models.claim import (
    Claim,
    Citation,
    CitationType,
    SourceType,
    ClaimsOutput,
    SearchSummary,
    ArticleWithoutFullText
)
from ..utils.llm_client import ClaudeClient
from ..utils.validators import ClaimValidator

logger = logging.getLogger(__name__)


class ClaimsGenerator:
    """Generates claims with complete substantiation and citations"""

    def __init__(self, claude_client: ClaudeClient):
        """
        Initialize claims generator

        Args:
            claude_client: Claude API client for claim extraction
        """
        self.claude = claude_client
        self.validator = ClaimValidator()

    async def generate_claims(
        self,
        search_results: SearchResults,
        ranked_articles: List[tuple[PubMedFullTextArticle, float]],
        clinical_trials: List[ClinicalTrialResult],
        user_intent: UserIntent,
        search_time: float,
        excluded_articles: List[Dict[str, Any]]
    ) -> ClaimsOutput:
        """
        Generate complete claims output from all sources

        Priority order:
        1. FDA Label (highest authority)
        2. Full-text articles (ranked by relevance)
        3. Trial registry data (supporting context)

        Args:
            search_results: Results from all sources
            ranked_articles: Full-text articles ranked by relevance
            clinical_trials: Clinical trial results
            user_intent: User's original intent
            search_time: Time taken for search
            excluded_articles: Articles without full text

        Returns:
            ClaimsOutput with all claims and metadata
        """
        logger.info("Generating claims from search results")

        claims = []
        claim_id = 1

        # 1. Generate FDA label claim (always highest priority)
        if search_results.fda_label:
            fda_claim = await self._generate_fda_claim(
                claim_id=claim_id,
                fda_label=search_results.fda_label,
                claim_type=user_intent.claim_type
            )
            if fda_claim:
                claims.append(fda_claim)
                claim_id += 1

        # 2. Generate claims from full-text articles (ranked order)
        target_claim_count = user_intent.output_requirements.claim_count
        articles_to_process = ranked_articles[:target_claim_count]  # Take top N

        for article, relevance_score in articles_to_process:
            if len(claims) >= target_claim_count:
                break

            article_claim = await self._generate_article_claim(
                claim_id=claim_id,
                article=article,
                clinical_trials=clinical_trials,
                claim_type=user_intent.claim_type,
                relevance_score=relevance_score
            )

            if article_claim:
                claims.append(article_claim)
                claim_id += 1

        # Build search summary
        search_summary = SearchSummary(
            user_query=user_intent.original_query,
            sources_searched=["OpenFDA", "PubMed/PMC", "ClinicalTrials.gov"],
            results_found={
                "fda_labels": 1 if search_results.fda_label else 0,
                "pubmed_total": search_results.pubmed_total_found,
                "pubmed_full_text": search_results.pubmed_full_text_available,
                "pubmed_abstract_only": search_results.pubmed_abstract_only,
                "clinical_trials": search_results.clinical_trials_found
            },
            full_text_strategy="Claims generated only from full-text articles (PMC)",
            search_time_seconds=search_time
        )

        # Build additional context
        additional_context = {
            "articles_without_full_text": [
                ArticleWithoutFullText(**article) for article in excluded_articles[:10]
            ],
            "recommendation": (
                f"{len(claims)} claims generated from full-text sources. "
                f"{len(excluded_articles)} additional relevant articles identified "
                f"but excluded due to lack of full text access."
            )
        }

        logger.info(f"Generated {len(claims)} claims")

        return ClaimsOutput(
            search_summary=search_summary,
            claims=claims,
            additional_context=additional_context
        )

    async def _generate_fda_claim(
        self,
        claim_id: int,
        fda_label: FDALabelResponse,
        claim_type: str
    ) -> Optional[Claim]:
        """
        Generate claim from FDA label

        Args:
            claim_id: Unique claim ID
            fda_label: FDA label data
            claim_type: Type of claim to extract

        Returns:
            Claim object or None if extraction fails
        """
        logger.info(f"Generating FDA label claim (type: {claim_type})")

        try:
            # Use LLM to extract claim from appropriate label section
            label_dict = fda_label.model_dump()
            claim_data = await self.claude.extract_fda_label_claim(
                label_data=label_dict,
                claim_type=claim_type
            )

            if not claim_data:
                logger.warning("Failed to extract FDA claim")
                return None

            # Validate completeness
            is_valid, issues = self.validator.validate_claim_completeness(claim_data)
            if not is_valid:
                logger.warning(f"FDA claim validation failed: {issues}")
                # Continue anyway - FDA labels are authoritative

            # Build citation
            brand_name = fda_label.brand_name or "Drug"
            effective_date = fda_label.effective_time or "current"

            citation = Citation(
                primary=True,
                citation_type=CitationType.FDA_LABEL,
                text=f"{brand_name} Prescribing Information. FDA-approved label. {effective_date}.",
                section=claim_type.title(),
                url="https://www.accessdata.fda.gov/scripts/cder/daf/"
            )

            # Build claim
            claim = Claim(
                claim_id=claim_id,
                claim_type=claim_type,
                claim_text=claim_data["claim_text"],
                substantiation=claim_data["substantiation"],
                source_type=SourceType.FDA_APPROVED_LABEL,
                citations=[citation],
                confidence="Highest - FDA Approved",
                full_text_used=True,
                extracted_from="FDA Label"
            )

            logger.info(f"Successfully generated FDA claim {claim_id}")
            return claim

        except Exception as e:
            logger.error(f"Error generating FDA claim: {e}")
            return None

    async def _generate_article_claim(
        self,
        claim_id: int,
        article: PubMedFullTextArticle,
        clinical_trials: List[ClinicalTrialResult],
        claim_type: str,
        relevance_score: float
    ) -> Optional[Claim]:
        """
        Generate claim from full-text article

        Args:
            claim_id: Unique claim ID
            article: Full-text article
            clinical_trials: Clinical trials for cross-referencing
            claim_type: Type of claim to extract
            relevance_score: Relevance score from ranking

        Returns:
            Claim object or None if extraction fails
        """
        logger.info(f"Generating claim from article {article.pmcid}")

        try:
            # Prepare article metadata
            article_metadata = {
                "title": article.title,
                "journal": article.journal,
                "authors": article.authors,
                "pmcid": article.pmcid,
                "doi": article.doi
            }

            # Use LLM to extract claim from full text
            claim_data = await self.claude.extract_claim_from_full_text(
                full_text=article.full_text,
                sections=article.sections,
                article_metadata=article_metadata,
                claim_type=claim_type
            )

            if not claim_data:
                logger.warning(f"Failed to extract claim from {article.pmcid}")
                return None

            # Validate completeness
            is_valid, issues = self.validator.validate_claim_completeness(claim_data)
            if not is_valid:
                logger.warning(f"Claim validation failed for {article.pmcid}: {issues}")
                return None

            # Validate numerical accuracy
            results_section = article.sections.get("Results", article.full_text[:2000])
            num_valid, num_issues = self.validator.validate_numerical_accuracy(
                claim_text=claim_data["claim_text"],
                substantiation=claim_data["substantiation"],
                source_text=results_section,
                numerical_data=claim_data.get("numerical_data", {})
            )

            if not num_valid:
                logger.warning(f"Numerical validation failed for {article.pmcid}: {num_issues}")
                # Continue anyway but note the issue

            # Build primary citation
            authors_str = ", ".join(article.authors[:3]) if article.authors else "Unknown"
            if len(article.authors) > 3:
                authors_str += " et al."

            primary_citation = Citation(
                primary=True,
                citation_type=CitationType.JOURNAL_ARTICLE,
                authors=authors_str,
                title=article.title,
                journal=article.journal,
                pmcid=article.pmcid,
                doi=article.doi,
                pmc_url=f"https://www.ncbi.nlm.nih.gov/pmc/articles/{article.pmcid}/",
                full_text_available=True
            )

            # Cross-reference with clinical trials
            trial_citation = self._find_trial_citation(article, clinical_trials)
            citations = [primary_citation]
            if trial_citation:
                citations.append(trial_citation)

            # Determine confidence based on validation
            if num_valid and relevance_score >= 20:
                confidence = "High - Full text substantiation with validated data"
            elif num_valid:
                confidence = "High - Full text substantiation"
            else:
                confidence = "Medium - Full text available but numerical validation flagged issues"

            # Build claim
            claim = Claim(
                claim_id=claim_id,
                claim_type=claim_type,
                claim_text=claim_data["claim_text"],
                substantiation=claim_data["substantiation"],
                source_type=SourceType.PEER_REVIEWED_FULL_TEXT,
                citations=citations,
                confidence=confidence,
                full_text_used=True,
                extracted_from=claim_data.get("extracted_from", "Results section"),
                numerical_data=claim_data.get("numerical_data", {})
            )

            logger.info(f"Successfully generated claim {claim_id} from {article.pmcid}")
            return claim

        except Exception as e:
            logger.error(f"Error generating claim from article {article.pmcid}: {e}")
            return None

    def _find_trial_citation(
        self,
        article: PubMedFullTextArticle,
        clinical_trials: List[ClinicalTrialResult]
    ) -> Optional[Citation]:
        """
        Find matching clinical trial for cross-reference

        Args:
            article: Full-text article
            clinical_trials: List of trials

        Returns:
            Citation for matching trial or None
        """
        # Simple heuristic: check if article title or text mentions NCT number
        full_text_lower = article.full_text.lower()

        for trial in clinical_trials:
            nct_lower = trial.nct_id.lower()
            if nct_lower in full_text_lower:
                return Citation(
                    primary=False,
                    citation_type=CitationType.TRIAL_REGISTRY,
                    text=f"{trial.brief_title or trial.official_title}",
                    nct=trial.nct_id,
                    url=trial.url
                )

        return None
