"""
Quality assurance validators (Phase 9)
Ensures numerical accuracy and data integrity
"""
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ClaimValidator:
    """Validates claims for accuracy and completeness"""

    @staticmethod
    def validate_numerical_accuracy(
        claim_text: str,
        substantiation: str,
        source_text: str,
        numerical_data: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Validate that all numbers in claim match source text exactly

        Args:
            claim_text: The claim statement
            substantiation: The substantiation paragraph
            source_text: Original source text
            numerical_data: Extracted numerical data

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []

        # Extract all percentages from claim and substantiation
        claim_numbers = ClaimValidator._extract_numbers(claim_text + " " + substantiation)
        source_numbers = ClaimValidator._extract_numbers(source_text)

        # Check that numbers in claim exist in source
        for number in claim_numbers:
            if number not in source_numbers:
                # Allow for minor formatting differences (e.g., "89%" vs "89 %")
                if not ClaimValidator._fuzzy_number_match(number, source_numbers):
                    issues.append(f"Number '{number}' in claim not found in source text")

        # Validate specific numerical data fields
        if numerical_data:
            for field, value in numerical_data.items():
                if value is not None:
                    value_str = str(value)
                    if not ClaimValidator._fuzzy_number_match(value_str, source_numbers):
                        issues.append(
                            f"Numerical data field '{field}' value '{value}' not found in source"
                        )

        is_valid = len(issues) == 0
        if not is_valid:
            logger.warning(f"Numerical validation failed: {issues}")

        return is_valid, issues

    @staticmethod
    def _extract_numbers(text: str) -> List[str]:
        """Extract all numbers and percentages from text"""
        # Pattern for numbers with optional decimals, commas, and % sign
        patterns = [
            r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?%?\b',  # Numbers with commas
            r'\b\d+\.\d+%?\b',  # Decimals
            r'\bN\s*=\s*\d+(?:,\d{3})*\b',  # Sample sizes
            r'\bp\s*[<>=]\s*0\.\d+\b',  # P-values
            r'\bCI:?\s*\d+%?-\d+%?\b',  # Confidence intervals
        ]

        numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            numbers.extend(matches)

        return [n.strip() for n in numbers]

    @staticmethod
    def _fuzzy_number_match(number: str, number_list: List[str]) -> bool:
        """Check if number matches any in list, allowing formatting differences"""
        # Remove spaces, normalize
        number_clean = number.replace(" ", "").replace(",", "").lower()

        for source_num in number_list:
            source_clean = source_num.replace(" ", "").replace(",", "").lower()
            if number_clean == source_clean:
                return True
            # Check if one contains the other (for cases like "89%" in "89% reduction")
            if number_clean in source_clean or source_clean in number_clean:
                return True

        return False

    @staticmethod
    def validate_claim_completeness(claim_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate that claim has all required fields

        Args:
            claim_data: Claim dictionary

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []

        required_fields = ["claim_text", "substantiation"]
        for field in required_fields:
            if not claim_data.get(field):
                issues.append(f"Missing required field: {field}")

        # Check minimum lengths
        claim_text = claim_data.get("claim_text", "")
        if len(claim_text) < 20:
            issues.append("Claim text too short (minimum 20 characters)")

        substantiation = claim_data.get("substantiation", "")
        if len(substantiation) < 100:
            issues.append("Substantiation too short (minimum 100 characters)")

        is_valid = len(issues) == 0
        return is_valid, issues

    @staticmethod
    def validate_full_text_requirement(
        full_text_available: bool,
        source_type: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that claim meets full text requirement

        Args:
            full_text_available: Was full text used?
            source_type: Source type

        Returns:
            Tuple of (is_valid, warning message)
        """
        if source_type == "FDA_APPROVED_LABEL":
            return True, None  # FDA labels are always acceptable

        if source_type == "PEER_REVIEWED_FULL_TEXT" and full_text_available:
            return True, None

        if source_type == "PEER_REVIEWED_ABSTRACT" or not full_text_available:
            return False, "Claim based on abstract only - full text not available"

        return True, None

    @staticmethod
    def validate_citation_completeness(citation: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate citation has required fields

        Args:
            citation: Citation dictionary

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []

        citation_type = citation.get("citation_type")

        if citation_type == "JOURNAL_ARTICLE":
            required = ["authors", "title", "journal", "year"]
            for field in required:
                if not citation.get(field):
                    issues.append(f"Missing required citation field: {field}")

            # Should have at least one identifier
            if not any([citation.get("pmid"), citation.get("doi"), citation.get("pmcid")]):
                issues.append("Missing article identifier (PMID, DOI, or PMCID required)")

        elif citation_type == "FDA_LABEL":
            if not citation.get("section"):
                issues.append("Missing FDA label section")

        elif citation_type == "TRIAL_REGISTRY":
            if not citation.get("nct"):
                issues.append("Missing NCT number")

        is_valid = len(issues) == 0
        return is_valid, issues


class SearchValidator:
    """Validates search results"""

    @staticmethod
    def validate_search_results(search_results: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate that search returned usable results

        Args:
            search_results: SearchResults object as dict

        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings = []

        # Check if any sources returned data
        has_fda = search_results.get("fda_label") is not None
        has_pubmed = len(search_results.get("pubmed_articles", [])) > 0
        has_trials = len(search_results.get("clinical_trials", [])) > 0

        if not any([has_fda, has_pubmed, has_trials]):
            warnings.append("No results found from any source")
            return False, warnings

        # Check full text availability
        pubmed_total = search_results.get("pubmed_total_found", 0)
        pubmed_full_text = search_results.get("pubmed_full_text_available", 0)

        if pubmed_total > 0 and pubmed_full_text == 0:
            warnings.append(
                f"Found {pubmed_total} PubMed articles but none have full text in PMC"
            )

        if pubmed_full_text < 3 and pubmed_total > 0:
            warnings.append(
                f"Only {pubmed_full_text}/{pubmed_total} articles have full text available"
            )

        # Check FDA label quality
        if has_fda:
            fda_label = search_results.get("fda_label", {})
            if not fda_label.get("indications_and_usage"):
                warnings.append("FDA label missing indications section")

        return True, warnings
