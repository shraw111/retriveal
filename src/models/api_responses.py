"""
Data models for API responses from external sources
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date


class FDALabelResponse(BaseModel):
    """OpenFDA label response"""
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    indications_and_usage: List[str] = Field(default_factory=list)
    clinical_studies: List[str] = Field(default_factory=list)
    dosage_and_administration: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    adverse_reactions: List[str] = Field(default_factory=list)
    effective_time: Optional[str] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class PubMedArticleMetadata(BaseModel):
    """PubMed article metadata from search"""
    pmid: str
    title: str
    abstract: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    pub_year: Optional[int] = None
    doi: Optional[str] = None
    pmcid: Optional[str] = None  # Critical for full text retrieval
    publication_types: List[str] = Field(default_factory=list)
    mesh_terms: List[str] = Field(default_factory=list)


class PubMedFullTextArticle(BaseModel):
    """Full text article from PubMed Central"""
    pmcid: str
    pmid: Optional[str] = None
    title: str
    abstract: Optional[str] = None
    full_text: str = Field(..., description="Complete article text")
    sections: Dict[str, str] = Field(
        default_factory=dict,
        description="Structured sections (Introduction, Methods, Results, Discussion)"
    )
    authors: List[str] = Field(default_factory=list)
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    references: List[str] = Field(default_factory=list)


class ClinicalTrialResult(BaseModel):
    """Clinical trial from ClinicalTrials.gov"""
    nct_id: str
    official_title: str
    brief_title: Optional[str] = None
    status: str
    phase: Optional[str] = None
    enrollment: Optional[int] = None
    start_date: Optional[str] = None
    completion_date: Optional[str] = None
    primary_outcome_measures: List[str] = Field(default_factory=list)
    secondary_outcome_measures: List[str] = Field(default_factory=list)
    intervention_type: Optional[str] = None
    intervention_name: Optional[str] = None
    sponsor: Optional[str] = None
    has_results: bool = False
    results_summary: Optional[str] = None
    url: str


class SearchResults(BaseModel):
    """Aggregated search results from all sources"""
    fda_label: Optional[FDALabelResponse] = None
    pubmed_articles: List[PubMedArticleMetadata] = Field(default_factory=list)
    pubmed_full_text: List[PubMedFullTextArticle] = Field(default_factory=list)
    clinical_trials: List[ClinicalTrialResult] = Field(default_factory=list)

    # Tracking
    pubmed_total_found: int = 0
    pubmed_full_text_available: int = 0
    pubmed_abstract_only: int = 0
    clinical_trials_found: int = 0
