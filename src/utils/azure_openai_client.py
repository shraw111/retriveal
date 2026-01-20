"""
Azure OpenAI API client for LLM-powered processing
Alternative to Claude API - supports Azure OpenAI Service

Used for:
- Phase 1: Intent extraction from free text
- Phase 5: Relevance scoring
- Phase 6: Claims generation from full text
"""
import logging
import json
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


class AzureOpenAIClient:
    """Client for Azure OpenAI API"""

    def __init__(
        self,
        api_key: str,
        azure_endpoint: str,
        api_version: str = "2024-02-15-preview",
        deployment_name: str = "gpt-4",
        max_retries: int = 3
    ):
        """
        Initialize Azure OpenAI client

        Args:
            api_key: Azure OpenAI API key
            azure_endpoint: Azure OpenAI endpoint URL
            api_version: API version
            deployment_name: Deployment/model name
            max_retries: Maximum retry attempts
        """
        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version
        )
        self.deployment_name = deployment_name
        self.max_retries = max_retries

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def extract_intent(self, user_query: str) -> Dict[str, Any]:
        """
        Phase 1: Extract structured intent from free-text query

        Args:
            user_query: User's free-text query

        Returns:
            Dictionary with extracted intent
        """
        prompt = f"""You are a pharmaceutical information assistant. Extract structured information from this user query about drug claims.

User Query: "{user_query}"

Extract the following information in JSON format:
{{
  "drug": {{
    "brand_name": "Brand name if mentioned (e.g., Paxlovid)",
    "generic_name": "Generic name if mentioned or can be inferred",
    "search_terms": ["list of all relevant search terms including brand, generic, and synonyms"]
  }},
  "claim_type": "Type of claim (efficacy, safety, dosing, mechanism, indication)",
  "indication": "Medical condition/indication",
  "population": "Target patient population (e.g., high-risk patients, adults, elderly)",
  "output_requirements": {{
    "claim_count": 6,
    "include_substantiation": true,
    "format_type": "MLR-ready",
    "include_safety": false,
    "include_dosing": false
  }}
}}

Important:
- If brand name is given but not generic, leave generic_name as null (will be looked up via OpenFDA)
- Default to "efficacy" if claim type is unclear
- Be generous with search_terms - include all variations
- Set include_safety to true only if explicitly requested
- Set include_dosing to true only if explicitly requested

Return ONLY valid JSON, no other text."""

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a pharmaceutical data extraction expert. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content
            logger.info(f"Intent extraction response: {response_text[:200]}...")

            # Parse JSON response
            intent_data = json.loads(response_text)
            return intent_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent JSON: {e}")
            logger.error(f"Response was: {response_text}")
            raise
        except Exception as e:
            logger.error(f"Error in intent extraction: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def score_relevance(
        self,
        article_text: str,
        user_intent: Dict[str, Any],
        max_score: int = 10
    ) -> float:
        """
        Phase 5: Score article relevance to user query

        Args:
            article_text: Article title and abstract/intro
            user_intent: User's intent object
            max_score: Maximum score

        Returns:
            Relevance score (0-max_score)
        """
        drug_name = user_intent.get("drug", {}).get("brand_name", "the drug")
        claim_type = user_intent.get("claim_type", "efficacy")
        indication = user_intent.get("indication", "")
        population = user_intent.get("population", "")

        prompt = f"""Rate the relevance of this article to the user's information need on a scale of 0-{max_score}.

User is looking for: {claim_type} claims for {drug_name} in {indication} for {population}

Article text (title + beginning):
{article_text[:1000]}

Consider:
- Does it study the correct drug?
- Does it address the right indication?
- Does it cover the requested claim type (efficacy/safety)?
- Is it the right patient population?
- Is it a rigorous clinical trial vs observational study?

Return ONLY a number from 0-{max_score}, no other text.
10 = Perfect match, highly relevant Phase 3 RCT
7-9 = Good match, relevant study
4-6 = Moderate match, some relevance
1-3 = Weak match, tangentially related
0 = Not relevant"""

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a relevance scorer. Return only a single number."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=10
            )

            response_text = response.choices[0].message.content.strip()
            score = float(response_text)
            return min(max(score, 0), max_score)  # Clamp to [0, max_score]

        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse relevance score: {e}")
            return 5.0  # Default to middle score
        except Exception as e:
            logger.error(f"Error in relevance scoring: {e}")
            return 5.0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def extract_claim_from_full_text(
        self,
        full_text: str,
        sections: Dict[str, str],
        article_metadata: Dict[str, Any],
        claim_type: str = "efficacy"
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 6: Extract claim from full-text article

        Args:
            full_text: Complete article text
            sections: Structured sections dictionary
            article_metadata: Article metadata (title, authors, journal, etc.)
            claim_type: Type of claim to extract

        Returns:
            Dictionary with claim_text, substantiation, numerical_data
        """
        # Focus on Results section
        results_section = sections.get("Results", "") or sections.get("RESULTS", "")
        if not results_section:
            # Try to find any section containing "results"
            for section_name, section_text in sections.items():
                if "result" in section_name.lower():
                    results_section = section_text
                    break

        if not results_section:
            logger.warning("No Results section found in article")
            results_section = full_text[:3000]  # Use first 3000 chars

        prompt = f"""You are a medical writer creating MLR-ready pharmaceutical claims. Extract a {claim_type} claim from this clinical trial article.

Article: {article_metadata.get('title', '')}
Journal: {article_metadata.get('journal', '')}
Authors: {', '.join(article_metadata.get('authors', [])[:3])}

Results Section:
{results_section[:3000]}

Extract:
1. **claim_text**: A concise, MLR-ready claim statement (1-2 sentences, no longer)
2. **substantiation**: A detailed paragraph with:
   - Study design (randomized, double-blind, etc.)
   - Population (N=, inclusion criteria)
   - Intervention (drug, dose, duration)
   - Comparator (placebo, active control)
   - Primary endpoint measured
   - Specific results with exact numbers
   - Risk reduction or effect size
   - Statistical significance (p-value, confidence interval)
   - Time frame

3. **numerical_data**: Extract exact numbers for validation:
   - sample_size: Total N
   - primary_endpoint_result: e.g., "0.58% vs 5.73%"
   - risk_reduction: e.g., "89%"
   - confidence_interval: e.g., "95% CI: 83%-93%"
   - p_value: e.g., "P<0.001"

CRITICAL RULES:
- Use EXACT numbers from the text - never round or approximate
- If a number says "89%", write "89%" not "approximately 90%"
- Include confidence intervals exactly as stated
- Quote statistical significance exactly
- If data is missing, return null for that field

Return JSON:
{{
  "claim_text": "Concise claim here",
  "substantiation": "Detailed paragraph here",
  "numerical_data": {{
    "sample_size": 2246,
    "primary_endpoint_result": "0.58% vs 5.73%",
    "risk_reduction": "89%",
    "confidence_interval": "95% CI: 83%-93%",
    "p_value": "P<0.001"
  }},
  "extracted_from": "Results section, paragraphs 3-5"
}}

Return ONLY valid JSON, no other text."""

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a medical writer. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content

            claim_data = json.loads(response_text)
            return claim_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse claim JSON: {e}")
            logger.error(f"Response was: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error extracting claim from full text: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def extract_fda_label_claim(
        self,
        label_data: Dict[str, Any],
        claim_type: str = "indication"
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 6: Extract claim from FDA label

        Args:
            label_data: FDA label data
            claim_type: Type of claim (indication, efficacy, safety, dosing)

        Returns:
            Dictionary with claim_text and substantiation
        """
        # Select appropriate section based on claim type
        if claim_type == "indication":
            section_data = label_data.get("indications_and_usage", [])
            section_name = "Indications and Usage"
        elif claim_type == "efficacy":
            section_data = label_data.get("clinical_studies", [])
            section_name = "Clinical Studies"
        elif claim_type == "safety":
            section_data = label_data.get("adverse_reactions", [])
            section_name = "Adverse Reactions"
        elif claim_type == "dosing":
            section_data = label_data.get("dosage_and_administration", [])
            section_name = "Dosage and Administration"
        else:
            section_data = label_data.get("indications_and_usage", [])
            section_name = "Indications and Usage"

        if not section_data:
            return None

        section_text = " ".join(section_data) if isinstance(section_data, list) else section_data

        brand_name = label_data.get("brand_name", "This drug")

        prompt = f"""Extract an MLR-ready claim from this FDA-approved label section.

Drug: {brand_name}
Section: {section_name}

Text:
{section_text[:2000]}

Create:
1. **claim_text**: Concise claim using FDA-approved language (1-2 sentences)
2. **substantiation**: The exact FDA label text that supports this claim

For indication claims, use the approved indication wording.
For efficacy claims, include specific data from clinical studies.

Return JSON:
{{
  "claim_text": "FDA-approved claim here",
  "substantiation": "Exact FDA label text here"
}}

Return ONLY valid JSON, no other text."""

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a medical writer. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content
            claim_data = json.loads(response_text)
            return claim_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse FDA claim JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting FDA claim: {e}")
            return None
