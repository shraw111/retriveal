"""
Data models for user intent extraction (Phase 1)
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class DrugIdentification(BaseModel):
    """Drug identification from user query"""
    brand_name: Optional[str] = Field(None, description="Brand name (e.g., Paxlovid)")
    generic_name: Optional[str] = Field(None, description="Generic name (e.g., nirmatrelvir/ritonavir)")
    synonyms: List[str] = Field(default_factory=list, description="Alternative names and synonyms")
    search_terms: List[str] = Field(default_factory=list, description="Optimized search terms")


class OutputRequirements(BaseModel):
    """User's output preferences"""
    claim_count: int = Field(default=6, ge=1, le=20, description="Number of claims to generate")
    include_substantiation: bool = Field(default=True, description="Include full substantiation text")
    format_type: str = Field(default="MLR-ready", description="Output format (MLR-ready, scientific, etc.)")
    include_safety: bool = Field(default=False, description="Include safety claims")
    include_dosing: bool = Field(default=False, description="Include dosing information")


class UserIntent(BaseModel):
    """Structured representation of user query intent"""
    original_query: str = Field(..., description="Original free-text query from user")
    drug: DrugIdentification = Field(..., description="Identified drug information")
    claim_type: str = Field(..., description="Type of claim requested (efficacy, safety, dosing, etc.)")
    indication: Optional[str] = Field(None, description="Medical indication/condition")
    population: Optional[str] = Field(None, description="Target patient population")
    output_requirements: OutputRequirements = Field(default_factory=OutputRequirements)

    class Config:
        json_schema_extra = {
            "example": {
                "original_query": "efficacy claims for Paxlovid in COVID-19 high-risk patients",
                "drug": {
                    "brand_name": "Paxlovid",
                    "generic_name": "nirmatrelvir/ritonavir",
                    "search_terms": ["Paxlovid", "nirmatrelvir", "ritonavir"]
                },
                "claim_type": "efficacy",
                "indication": "COVID-19",
                "population": "high-risk patients",
                "output_requirements": {
                    "claim_count": 6,
                    "include_substantiation": True,
                    "format_type": "MLR-ready"
                }
            }
        }
