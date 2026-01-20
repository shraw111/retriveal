"""
Basic tests for the Drug Claims Retrieval System
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

# Test intent parsing
def test_user_intent_model():
    """Test UserIntent data model"""
    from src.models.intent import UserIntent, DrugIdentification, OutputRequirements

    intent = UserIntent(
        original_query="efficacy claims for Paxlovid",
        drug=DrugIdentification(
            brand_name="Paxlovid",
            generic_name="nirmatrelvir/ritonavir",
            search_terms=["Paxlovid", "nirmatrelvir"]
        ),
        claim_type="efficacy",
        indication="COVID-19",
        population="high-risk patients"
    )

    assert intent.drug.brand_name == "Paxlovid"
    assert intent.claim_type == "efficacy"
    assert "Paxlovid" in intent.drug.search_terms


def test_claim_model():
    """Test Claim data model"""
    from src.models.claim import Claim, Citation, CitationType, SourceType

    citation = Citation(
        primary=True,
        citation_type=CitationType.FDA_LABEL,
        text="Test citation",
        section="Indications"
    )

    claim = Claim(
        claim_id=1,
        claim_type="efficacy",
        claim_text="Test claim text",
        substantiation="Test substantiation",
        source_type=SourceType.FDA_APPROVED_LABEL,
        citations=[citation],
        confidence="High",
        full_text_used=True
    )

    assert claim.claim_id == 1
    assert claim.source_type == SourceType.FDA_APPROVED_LABEL
    assert len(claim.citations) == 1
    assert claim.full_text_used is True


# Test API response models
def test_fda_label_response():
    """Test FDALabelResponse model"""
    from src.models.api_responses import FDALabelResponse

    label = FDALabelResponse(
        brand_name="Paxlovid",
        generic_name="nirmatrelvir/ritonavir",
        indications_and_usage=["Test indication"],
        clinical_studies=["Test study"]
    )

    assert label.brand_name == "Paxlovid"
    assert len(label.indications_and_usage) == 1


def test_pubmed_article_metadata():
    """Test PubMedArticleMetadata model"""
    from src.models.api_responses import PubMedArticleMetadata

    article = PubMedArticleMetadata(
        pmid="12345678",
        title="Test Article",
        abstract="Test abstract",
        authors=["Smith J", "Doe J"],
        journal="Test Journal",
        pmcid="PMC1234567"
    )

    assert article.pmid == "12345678"
    assert article.pmcid == "PMC1234567"
    assert len(article.authors) == 2


# Test validators
def test_claim_validator_completeness():
    """Test ClaimValidator.validate_claim_completeness"""
    from src.utils.validators import ClaimValidator

    validator = ClaimValidator()

    # Valid claim
    valid_claim = {
        "claim_text": "This is a valid claim with enough text",
        "substantiation": "This is substantiation text that is long enough to pass validation. " * 3
    }
    is_valid, issues = validator.validate_claim_completeness(valid_claim)
    assert is_valid is True
    assert len(issues) == 0

    # Invalid claim - missing substantiation
    invalid_claim = {
        "claim_text": "This is a claim",
        "substantiation": ""
    }
    is_valid, issues = validator.validate_claim_completeness(invalid_claim)
    assert is_valid is False
    assert len(issues) > 0


def test_claim_validator_full_text():
    """Test ClaimValidator.validate_full_text_requirement"""
    from src.utils.validators import ClaimValidator

    validator = ClaimValidator()

    # FDA label - always valid
    is_valid, warning = validator.validate_full_text_requirement(
        full_text_available=True,
        source_type="FDA_APPROVED_LABEL"
    )
    assert is_valid is True
    assert warning is None

    # Full text available - valid
    is_valid, warning = validator.validate_full_text_requirement(
        full_text_available=True,
        source_type="PEER_REVIEWED_FULL_TEXT"
    )
    assert is_valid is True

    # Abstract only - invalid
    is_valid, warning = validator.validate_full_text_requirement(
        full_text_available=False,
        source_type="PEER_REVIEWED_ABSTRACT"
    )
    assert is_valid is False
    assert warning is not None


def test_search_validator():
    """Test SearchValidator.validate_search_results"""
    from src.utils.validators import SearchValidator

    validator = SearchValidator()

    # Valid search results
    valid_results = {
        "fda_label": {"brand_name": "Test"},
        "pubmed_articles": [{"pmid": "123"}],
        "clinical_trials": [],
        "pubmed_total_found": 10,
        "pubmed_full_text_available": 5
    }
    is_valid, warnings = validator.validate_search_results(valid_results)
    assert is_valid is True

    # Invalid - no results
    invalid_results = {
        "fda_label": None,
        "pubmed_articles": [],
        "clinical_trials": [],
        "pubmed_total_found": 0,
        "pubmed_full_text_available": 0
    }
    is_valid, warnings = validator.validate_search_results(invalid_results)
    assert is_valid is False


# Integration test (requires actual API keys)
@pytest.mark.skip(reason="Requires API keys and network access")
@pytest.mark.asyncio
async def test_full_pipeline():
    """Integration test of full pipeline (requires API keys)"""
    from src.main import DrugClaimsRetrieval

    system = DrugClaimsRetrieval()
    query = "efficacy claims for aspirin in cardiovascular disease"

    result = await system.process_query(query)

    assert result is not None
    assert len(result.claims) > 0
    assert result.search_summary.user_query == query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
