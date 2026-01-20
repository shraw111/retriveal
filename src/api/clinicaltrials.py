"""
ClinicalTrials.gov API v2 client
Phase 2-4: Parallel search execution
"""
import aiohttp
import logging
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models.api_responses import ClinicalTrialResult

logger = logging.getLogger(__name__)


class ClinicalTrialsClient:
    """Client for ClinicalTrials.gov API v2"""

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def __init__(self, timeout: int = 30, page_size: int = 10):
        """
        Initialize ClinicalTrials.gov client

        Args:
            timeout: Request timeout in seconds
            page_size: Number of results per page (max 100)
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.page_size = min(page_size, 100)  # API max is 100

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def search_trials(
        self,
        drug_name: str,
        indication: Optional[str] = None,
        phase: Optional[str] = "PHASE3",
        status: Optional[str] = "COMPLETED"
    ) -> List[ClinicalTrialResult]:
        """
        Search ClinicalTrials.gov for trials

        Args:
            drug_name: Drug name to search
            indication: Medical indication
            phase: Trial phase (PHASE1, PHASE2, PHASE3, PHASE4)
            status: Trial status (COMPLETED, RECRUITING, etc.)

        Returns:
            List of ClinicalTrialResult
        """
        # Build query
        query_parts = [drug_name]
        if indication:
            query_parts.append(indication)
        query = " AND ".join(query_parts)

        logger.info(f"Searching ClinicalTrials.gov for: {query}")

        params = {
            "query.term": query,
            "pageSize": self.page_size,
            "format": "json"
        }

        # Add filters
        if status:
            params["filter.overallStatus"] = status
        if phase:
            params["filter.phase"] = phase

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()

                    studies = data.get("studies", [])
                    logger.info(f"Found {len(studies)} clinical trials")

                    results = []
                    for study in studies:
                        trial = self._parse_trial(study)
                        if trial:
                            results.append(trial)

                    return results

        except aiohttp.ClientError as e:
            logger.error(f"ClinicalTrials.gov API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in ClinicalTrials search: {e}")
            return []

    def _parse_trial(self, study_data: dict) -> Optional[ClinicalTrialResult]:
        """Parse study JSON into ClinicalTrialResult"""
        try:
            protocol_section = study_data.get("protocolSection", {})
            identification = protocol_section.get("identificationModule", {})
            status_module = protocol_section.get("statusModule", {})
            design_module = protocol_section.get("designModule", {})
            arms_module = protocol_section.get("armsInterventionsModule", {})
            outcomes_module = protocol_section.get("outcomesModule", {})
            sponsor_module = protocol_section.get("sponsorCollaboratorsModule", {})

            # NCT ID
            nct_id = identification.get("nctId")
            if not nct_id:
                return None

            # Titles
            official_title = identification.get("officialTitle", "")
            brief_title = identification.get("briefTitle", "")

            # Status
            status = status_module.get("overallStatus", "UNKNOWN")

            # Phase
            phases = design_module.get("phases", [])
            phase = phases[0] if phases else None

            # Enrollment
            enrollment_info = design_module.get("enrollmentInfo", {})
            enrollment = enrollment_info.get("count")

            # Dates
            start_date_struct = status_module.get("startDateStruct", {})
            start_date = start_date_struct.get("date")

            completion_date_struct = status_module.get("completionDateStruct", {})
            completion_date = completion_date_struct.get("date")

            # Primary outcome measures
            primary_outcomes = outcomes_module.get("primaryOutcomes", [])
            primary_measures = [
                outcome.get("measure", "")
                for outcome in primary_outcomes
            ]

            # Secondary outcome measures
            secondary_outcomes = outcomes_module.get("secondaryOutcomes", [])
            secondary_measures = [
                outcome.get("measure", "")
                for outcome in secondary_outcomes
            ]

            # Interventions
            interventions = arms_module.get("interventions", [])
            intervention_type = None
            intervention_name = None
            if interventions:
                intervention_type = interventions[0].get("type")
                intervention_name = interventions[0].get("name")

            # Sponsor
            lead_sponsor = sponsor_module.get("leadSponsor", {})
            sponsor = lead_sponsor.get("name")

            # Results availability
            has_results = "resultsSection" in study_data
            results_summary = None
            if has_results:
                results_section = study_data.get("resultsSection", {})
                # Try to extract summary if available
                # This is simplified - actual results parsing can be quite complex
                results_summary = "Results available on ClinicalTrials.gov"

            # Construct URL
            url = f"https://clinicaltrials.gov/study/{nct_id}"

            return ClinicalTrialResult(
                nct_id=nct_id,
                official_title=official_title,
                brief_title=brief_title,
                status=status,
                phase=phase,
                enrollment=enrollment,
                start_date=start_date,
                completion_date=completion_date,
                primary_outcome_measures=primary_measures,
                secondary_outcome_measures=secondary_measures,
                intervention_type=intervention_type,
                intervention_name=intervention_name,
                sponsor=sponsor,
                has_results=has_results,
                results_summary=results_summary,
                url=url
            )

        except Exception as e:
            logger.error(f"Error parsing clinical trial: {e}")
            return None
