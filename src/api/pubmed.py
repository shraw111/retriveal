"""
PubMed/PMC API client with 3-step full-text retrieval
Phase 2-4: Parallel search execution

Steps:
1. Search PubMed for PMIDs (esearch)
2. Fetch metadata to get PMC IDs (esummary/efetch)
3. Fetch full text from PMC (efetch with pmc database)
"""
import asyncio
import aiohttp
import logging
import xml.etree.ElementTree as ET
from typing import List, Optional
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models.api_responses import PubMedArticleMetadata, PubMedFullTextArticle

logger = logging.getLogger(__name__)


class PubMedClient:
    """Client for PubMed and PubMed Central APIs using NCBI E-utilities"""

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        timeout: int = 30,
        max_results: int = 20
    ):
        """
        Initialize PubMed client

        Args:
            api_key: NCBI API key (optional but recommended for higher rate limits)
            email: Email address (required by NCBI if using API key)
            timeout: Request timeout in seconds
            max_results: Maximum number of articles to retrieve
        """
        self.api_key = api_key
        self.email = email
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_results = max_results

    async def search_articles(
        self,
        query: str,
        drug_name: str,
        indication: Optional[str] = None,
        population: Optional[str] = None,
        years_back: int = 5
    ) -> List[str]:
        """
        Step 1: Search PubMed for relevant articles, return PMIDs

        Args:
            query: Base search query
            drug_name: Drug name for search
            indication: Medical indication
            population: Target population
            years_back: How many years back to search

        Returns:
            List of PMIDs
        """
        # Build comprehensive search query
        search_terms = [f"({drug_name})"]

        if indication:
            search_terms.append(f"({indication})")

        if population:
            search_terms.append(f"({population})")

        # Add publication type filters for clinical trials
        search_terms.append("(clinical trial[Publication Type] OR randomized controlled trial[Publication Type])")

        full_query = " AND ".join(search_terms)

        # Date filter
        min_date = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y/%m/%d")
        max_date = datetime.now().strftime("%Y/%m/%d")

        logger.info(f"Searching PubMed with query: {full_query}")

        params = {
            "db": "pubmed",
            "term": full_query,
            "retmax": self.max_results,
            "retmode": "json",
            "sort": "pub_date",
            "mindate": min_date,
            "maxdate": max_date
        }

        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.ESEARCH_URL, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()

                    pmids = data.get("esearchresult", {}).get("idlist", [])
                    logger.info(f"Found {len(pmids)} PubMed articles")
                    return pmids

        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def get_article_metadata(self, pmids: List[str]) -> List[PubMedArticleMetadata]:
        """
        Step 2: Fetch metadata for PMIDs to find PMC IDs

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of PubMedArticleMetadata with PMC IDs where available
        """
        if not pmids:
            return []

        logger.info(f"Fetching metadata for {len(pmids)} articles")

        # Use efetch to get detailed XML records
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract"
        }

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.EFETCH_URL, params=params) as response:
                    response.raise_for_status()
                    xml_content = await response.text()

                    # Parse XML
                    root = ET.fromstring(xml_content)
                    articles = []

                    for article_elem in root.findall(".//PubmedArticle"):
                        metadata = self._parse_article_metadata(article_elem)
                        if metadata:
                            articles.append(metadata)

                    logger.info(f"Parsed {len(articles)} article metadata records")
                    pmcid_count = sum(1 for a in articles if a.pmcid)
                    logger.info(f"Articles with PMC IDs: {pmcid_count}/{len(articles)}")

                    return articles

        except Exception as e:
            logger.error(f"Error fetching article metadata: {e}")
            return []

    def _parse_article_metadata(self, article_elem: ET.Element) -> Optional[PubMedArticleMetadata]:
        """Parse XML article element into metadata object"""
        try:
            medline_citation = article_elem.find(".//MedlineCitation")
            article = medline_citation.find(".//Article")

            # PMID
            pmid_elem = medline_citation.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else None

            if not pmid:
                return None

            # Title
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "No title"

            # Abstract
            abstract_texts = article.findall(".//AbstractText")
            abstract = " ".join([a.text for a in abstract_texts if a.text]) if abstract_texts else None

            # Authors
            authors = []
            for author in article.findall(".//Author"):
                last = author.find("LastName")
                first = author.find("ForeName")
                if last is not None:
                    author_name = last.text
                    if first is not None:
                        author_name = f"{last.text} {first.text[0]}"
                    authors.append(author_name)

            # Journal
            journal_elem = article.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else None

            # Publication date
            pub_date = article.find(".//Journal/JournalIssue/PubDate")
            year = None
            pub_date_str = None
            if pub_date is not None:
                year_elem = pub_date.find("Year")
                if year_elem is not None:
                    year = int(year_elem.text)
                    pub_date_str = year_elem.text

            # DOI
            doi = None
            for article_id in article_elem.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text
                    break

            # CRITICAL: PMC ID for full text retrieval
            pmcid = None
            for article_id in article_elem.findall(".//ArticleId"):
                if article_id.get("IdType") == "pmc":
                    pmcid = article_id.text
                    break

            # Publication types
            pub_types = [pt.text for pt in article.findall(".//PublicationType") if pt.text]

            return PubMedArticleMetadata(
                pmid=pmid,
                title=title,
                abstract=abstract,
                authors=authors[:3] if len(authors) > 3 else authors,  # Limit to first 3
                journal=journal,
                publication_date=pub_date_str,
                pub_year=year,
                doi=doi,
                pmcid=pmcid,
                publication_types=pub_types
            )

        except Exception as e:
            logger.error(f"Error parsing article metadata: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def get_full_text_article(self, pmcid: str) -> Optional[PubMedFullTextArticle]:
        """
        Step 3: Fetch full text from PubMed Central

        Args:
            pmcid: PubMed Central ID (e.g., "PMC8908851")

        Returns:
            PubMedFullTextArticle with complete text and sections
        """
        # Remove PMC prefix if present
        pmc_id_clean = pmcid.replace("PMC", "")

        logger.info(f"Fetching full text for {pmcid}")

        params = {
            "db": "pmc",
            "id": pmc_id_clean,
            "retmode": "xml"
        }

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.EFETCH_URL, params=params) as response:
                    response.raise_for_status()
                    xml_content = await response.text()

                    # Parse PMC XML
                    root = ET.fromstring(xml_content)
                    return self._parse_pmc_full_text(root, pmcid)

        except Exception as e:
            logger.error(f"Error fetching full text for {pmcid}: {e}")
            return None

    def _parse_pmc_full_text(self, root: ET.Element, pmcid: str) -> Optional[PubMedFullTextArticle]:
        """Parse PMC XML into structured full text article"""
        try:
            article = root.find(".//article")
            if article is None:
                return None

            # Metadata
            front = article.find(".//front")
            title_elem = front.find(".//article-title") if front is not None else None
            title = self._get_element_text(title_elem) if title_elem is not None else "No title"

            # Abstract
            abstract_elem = front.find(".//abstract") if front is not None else None
            abstract = self._get_element_text(abstract_elem) if abstract_elem is not None else None

            # Authors
            authors = []
            if front is not None:
                for contrib in front.findall(".//contrib[@contrib-type='author']"):
                    name = contrib.find(".//name")
                    if name is not None:
                        surname = name.find("surname")
                        given_names = name.find("given-names")
                        if surname is not None:
                            author_name = surname.text
                            if given_names is not None:
                                author_name = f"{surname.text} {given_names.text}"
                            authors.append(author_name)

            # Journal
            journal_elem = front.find(".//journal-title") if front is not None else None
            journal = journal_elem.text if journal_elem is not None else None

            # Body sections
            body = article.find(".//body")
            sections = {}
            full_text_parts = []

            if body is not None:
                for sec in body.findall(".//sec"):
                    title_elem = sec.find("title")
                    section_title = title_elem.text if title_elem is not None else "Untitled"
                    section_text = self._get_element_text(sec)
                    sections[section_title] = section_text
                    full_text_parts.append(f"## {section_title}\n{section_text}\n")

            # Combine all text
            full_text = "\n\n".join(full_text_parts)

            # PMC URL
            doi = None
            if front is not None:
                for article_id in front.findall(".//article-id"):
                    if article_id.get("pub-id-type") == "doi":
                        doi = article_id.text

            return PubMedFullTextArticle(
                pmcid=pmcid,
                title=title,
                abstract=abstract,
                full_text=full_text,
                sections=sections,
                authors=authors[:5],  # Limit to 5 authors
                journal=journal,
                doi=doi
            )

        except Exception as e:
            logger.error(f"Error parsing PMC full text: {e}")
            return None

    def _get_element_text(self, element: Optional[ET.Element]) -> str:
        """Recursively extract all text from an XML element"""
        if element is None:
            return ""

        text_parts = []
        if element.text:
            text_parts.append(element.text.strip())

        for child in element:
            child_text = self._get_element_text(child)
            if child_text:
                text_parts.append(child_text)
            if child.tail:
                text_parts.append(child.tail.strip())

        return " ".join(text_parts)

    async def search_and_get_full_text(
        self,
        drug_name: str,
        indication: Optional[str] = None,
        population: Optional[str] = None
    ) -> tuple[List[PubMedArticleMetadata], List[PubMedFullTextArticle]]:
        """
        Complete 3-step workflow: Search → Metadata → Full Text

        Args:
            drug_name: Drug name to search
            indication: Medical indication
            population: Target population

        Returns:
            Tuple of (all articles metadata, full text articles only)
        """
        # Step 1: Search for PMIDs
        pmids = await self.search_articles(
            query="",
            drug_name=drug_name,
            indication=indication,
            population=population
        )

        if not pmids:
            logger.warning("No PubMed articles found")
            return [], []

        # Step 2: Get metadata (including PMC IDs)
        all_articles = await self.get_article_metadata(pmids)

        # Filter articles with PMC IDs
        articles_with_pmc = [a for a in all_articles if a.pmcid]
        logger.info(f"Articles with full text available: {len(articles_with_pmc)}/{len(all_articles)}")

        if not articles_with_pmc:
            logger.warning("No articles have full text in PMC")
            return all_articles, []

        # Step 3: Fetch full text for articles with PMC IDs
        full_text_tasks = [
            self.get_full_text_article(article.pmcid)
            for article in articles_with_pmc
        ]

        full_text_articles = await asyncio.gather(*full_text_tasks, return_exceptions=True)

        # Filter out None and exceptions
        valid_full_text = [
            article for article in full_text_articles
            if article is not None and not isinstance(article, Exception)
        ]

        logger.info(f"Successfully retrieved {len(valid_full_text)} full text articles")

        return all_articles, valid_full_text
