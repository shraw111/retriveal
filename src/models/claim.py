"""
Data models for claims and citations (Phase 6-8)
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Types of evidence sources"""
    FDA_APPROVED_LABEL = "FDA_APPROVED_LABEL"
    PEER_REVIEWED_FULL_TEXT = "PEER_REVIEWED_FULL_TEXT"
    PEER_REVIEWED_ABSTRACT = "PEER_REVIEWED_ABSTRACT"
    CLINICAL_TRIAL_REGISTRY = "CLINICAL_TRIAL_REGISTRY"
    FDA_CLINICAL_STUDIES = "FDA_CLINICAL_STUDIES"


class CitationType(str, Enum):
    """Types of citations"""
    FDA_LABEL = "FDA_LABEL"
    JOURNAL_ARTICLE = "JOURNAL_ARTICLE"
    TRIAL_REGISTRY = "TRIAL_REGISTRY"


class Citation(BaseModel):
    """Citation for a claim"""
    primary: bool = Field(..., description="Is this the primary citation?")
    citation_type: CitationType = Field(..., description="Type of citation")
    text: Optional[str] = Field(None, description="Formatted citation text")

    # Journal article fields
    authors: Optional[str] = Field(None, description="Authors (e.g., 'Hammond J, et al.')")
    title: Optional[str] = Field(None, description="Article title")
    journal: Optional[str] = Field(None, description="Journal name")
    year: Optional[int] = Field(None, description="Publication year")
    volume: Optional[str] = Field(None, description="Volume")
    issue: Optional[str] = Field(None, description="Issue")
    pages: Optional[str] = Field(None, description="Page range")
    pmid: Optional[str] = Field(None, description="PubMed ID")
    pmcid: Optional[str] = Field(None, description="PubMed Central ID")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    pmc_url: Optional[str] = Field(None, description="Direct link to PMC full text")
    full_text_available: bool = Field(default=False, description="Is full text available in PMC?")

    # FDA label fields
    section: Optional[str] = Field(None, description="Section of FDA label")

    # Trial registry fields
    nct: Optional[str] = Field(None, description="ClinicalTrials.gov NCT number")
    url: Optional[str] = Field(None, description="Direct URL to source")


class Claim(BaseModel):
    """Generated claim with full substantiation"""
    claim_id: int = Field(..., description="Unique claim identifier")
    claim_type: str = Field(..., description="Type of claim (indication, efficacy, safety, etc.)")
    claim_text: str = Field(..., description="The actual claim statement (concise, MLR-ready)")
    substantiation: str = Field(..., description="Detailed substantiation paragraph with data")
    source_type: SourceType = Field(..., description="Primary source type")
    citations: List[Citation] = Field(..., description="All supporting citations")
    confidence: str = Field(..., description="Confidence level (Highest, High, Medium, Low)")
    full_text_used: bool = Field(..., description="Was claim generated from full text?")
    extracted_from: Optional[str] = Field(None, description="Specific section/paragraph used")

    # Extracted data for validation
    numerical_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured numerical data for QA validation"
    )


class ArticleWithoutFullText(BaseModel):
    """Article that was relevant but excluded due to lack of full text"""
    pmid: str
    title: str
    journal: str
    year: Optional[int] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    note: str = "Relevant but full text not available in PMC - paywalled"
    doi: Optional[str] = None


class SearchSummary(BaseModel):
    """Summary of search execution"""
    user_query: str
    sources_searched: List[str] = ["OpenFDA", "PubMed/PMC", "ClinicalTrials.gov"]
    results_found: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of results from each source"
    )
    full_text_strategy: str = "Claims generated only from full-text articles (PMC)"
    search_time_seconds: float
    timestamp: datetime = Field(default_factory=datetime.now)


class ClaimsOutput(BaseModel):
    """Complete output structure (Phase 8)"""
    search_summary: SearchSummary
    claims: List[Claim]
    additional_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Articles without full text and recommendations"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "search_summary": {
                    "user_query": "efficacy claims for Paxlovid in COVID-19",
                    "sources_searched": ["OpenFDA", "PubMed/PMC", "ClinicalTrials.gov"],
                    "results_found": {
                        "fda_labels": 1,
                        "pubmed_total": 20,
                        "pubmed_full_text": 6,
                        "pubmed_abstract_only": 14,
                        "clinical_trials": 3
                    },
                    "search_time_seconds": 10.3
                },
                "claims": [],
                "additional_context": {
                    "articles_without_full_text": [],
                    "recommendation": "6 claims generated from full-text sources."
                }
            }
        }
