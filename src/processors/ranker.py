"""
Results Ranker - Phase 5: Results Processing & Ranking
Scores and ranks articles by relevance, recency, and source authority
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

from ..models.api_responses import PubMedFullTextArticle, SearchResults
from ..models.intent import UserIntent
from ..utils.llm_client import ClaudeClient

logger = logging.getLogger(__name__)


class ResultsRanker:
    """Ranks and filters search results by relevance"""

    def __init__(self, claude_client: ClaudeClient):
        """
        Initialize ranker

        Args:
            claude_client: Claude API client for relevance scoring
        """
        self.claude = claude_client

    async def rank_articles(
        self,
        articles: List[PubMedFullTextArticle],
        user_intent: UserIntent
    ) -> List[tuple[PubMedFullTextArticle, float]]:
        """
        Rank full-text articles by relevance

        Scoring factors:
        - Source authority: 8-9/10 for peer-reviewed RCTs
        - Relevance: 0-10 (LLM-scored match to query)
        - Recency: 0-5 (newer = better)

        Total score = authority + relevance + recency

        Args:
            articles: List of full-text articles
            user_intent: User intent for relevance scoring

        Returns:
            List of (article, score) tuples, sorted by score (highest first)
        """
        logger.info(f"Ranking {len(articles)} full-text articles")

        if not articles:
            return []

        # Score all articles in parallel
        import asyncio
        scoring_tasks = [
            self._score_article(article, user_intent)
            for article in articles
        ]

        scores = await asyncio.gather(*scoring_tasks, return_exceptions=True)

        # Combine articles with scores
        ranked = []
        for article, score_result in zip(articles, scores):
            if isinstance(score_result, Exception):
                logger.error(f"Error scoring article {article.pmcid}: {score_result}")
                score = 10.0  # Default middle score
            else:
                score = score_result

            ranked.append((article, score))

        # Sort by score (highest first)
        ranked.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Ranked articles. Top score: {ranked[0][1]:.1f}, "
                   f"Lowest score: {ranked[-1][1]:.1f}")

        return ranked

    async def _score_article(
        self,
        article: PubMedFullTextArticle,
        user_intent: UserIntent
    ) -> float:
        """
        Calculate relevance score for a single article

        Args:
            article: Full-text article
            user_intent: User intent

        Returns:
            Total score (0-24 scale: authority 8-9 + relevance 0-10 + recency 0-5)
        """
        # Source authority: 8-9 for peer-reviewed full text
        # (Could be enhanced by checking journal impact factor, study design, etc.)
        authority_score = 8.5

        # Relevance: Use LLM to score 0-10
        article_preview = f"{article.title}\n\n"
        if article.abstract:
            article_preview += f"Abstract: {article.abstract[:500]}"

        # Get structured results section if available
        results_section = article.sections.get("Results", "")
        if results_section:
            article_preview += f"\n\nResults: {results_section[:500]}"

        intent_dict = user_intent.model_dump()
        relevance_score = await self.claude.score_relevance(
            article_text=article_preview,
            user_intent=intent_dict,
            max_score=10
        )

        # Recency: 0-5 points based on publication year
        # (Not available in our simplified model, but could be added)
        recency_score = 3.0  # Default middle score

        total_score = authority_score + relevance_score + recency_score

        logger.debug(f"Article {article.pmcid} score: "
                    f"authority={authority_score:.1f}, "
                    f"relevance={relevance_score:.1f}, "
                    f"recency={recency_score:.1f}, "
                    f"total={total_score:.1f}")

        return total_score

    def filter_full_text_only(self, search_results: SearchResults) -> SearchResults:
        """
        Filter results to keep only articles with full text

        This enforces the requirement that claims should only be generated
        from complete articles, not abstracts.

        Args:
            search_results: Search results from all sources

        Returns:
            Filtered SearchResults with only full-text articles
        """
        logger.info("Filtering results for full text availability")

        # PubMed articles are already filtered - pubmed_full_text only contains
        # articles that have PMC IDs and full text was successfully retrieved

        full_text_count = len(search_results.pubmed_full_text)
        abstract_only_count = search_results.pubmed_abstract_only

        logger.info(f"Full text available: {full_text_count}")
        logger.info(f"Abstract only (excluded): {abstract_only_count}")

        if full_text_count == 0 and search_results.pubmed_total_found > 0:
            logger.warning(
                f"No full text available for {search_results.pubmed_total_found} "
                f"PubMed articles - all are paywalled or not in PMC"
            )

        return search_results

    def get_excluded_articles(
        self,
        search_results: SearchResults
    ) -> List[Dict[str, Any]]:
        """
        Get list of articles that were excluded due to lack of full text

        Args:
            search_results: Search results

        Returns:
            List of article metadata for excluded articles
        """
        excluded = []

        # Find articles without PMC IDs (no full text available)
        for article in search_results.pubmed_articles:
            if not article.pmcid:
                excluded.append({
                    "pmid": article.pmid,
                    "title": article.title,
                    "journal": article.journal,
                    "year": article.pub_year,
                    "authors": ", ".join(article.authors[:3]) if article.authors else None,
                    "abstract": article.abstract[:200] + "..." if article.abstract else None,
                    "note": "Relevant but full text not available in PMC - paywalled",
                    "doi": article.doi
                })

        logger.info(f"Excluded {len(excluded)} articles without full text")
        return excluded
