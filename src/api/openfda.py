"""
OpenFDA API client for retrieving FDA-approved drug labels
Phase 2-4: Parallel search execution
"""
import aiohttp
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models.api_responses import FDALabelResponse

logger = logging.getLogger(__name__)


class OpenFDAClient:
    """Client for OpenFDA Drug Label API"""

    BASE_URL = "https://api.fda.gov/drug/label.json"

    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def search_by_brand_name(self, brand_name: str) -> Optional[FDALabelResponse]:
        """
        Search FDA label by brand name

        Args:
            brand_name: Brand name of the drug (e.g., "Paxlovid")

        Returns:
            FDALabelResponse or None if not found
        """
        logger.info(f"Searching OpenFDA for brand name: {brand_name}")

        params = {
            "search": f'openfda.brand_name:"{brand_name}"',
            "limit": 1
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 404:
                        logger.warning(f"No FDA label found for brand name: {brand_name}")
                        return None

                    response.raise_for_status()
                    data = await response.json()

                    if "results" not in data or len(data["results"]) == 0:
                        logger.warning(f"No results in FDA response for: {brand_name}")
                        return None

                    return self._parse_label(data["results"][0])

        except aiohttp.ClientError as e:
            logger.error(f"OpenFDA API error for {brand_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenFDA search: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def search_by_generic_name(self, generic_name: str) -> Optional[FDALabelResponse]:
        """
        Fallback: Search FDA label by generic name

        Args:
            generic_name: Generic name of the drug (e.g., "nirmatrelvir")

        Returns:
            FDALabelResponse or None if not found
        """
        logger.info(f"Searching OpenFDA for generic name: {generic_name}")

        params = {
            "search": f'openfda.generic_name:"{generic_name}"',
            "limit": 1
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 404:
                        logger.warning(f"No FDA label found for generic name: {generic_name}")
                        return None

                    response.raise_for_status()
                    data = await response.json()

                    if "results" not in data or len(data["results"]) == 0:
                        return None

                    return self._parse_label(data["results"][0])

        except aiohttp.ClientError as e:
            logger.error(f"OpenFDA API error for {generic_name}: {e}")
            raise

    async def search(
        self,
        brand_name: Optional[str] = None,
        generic_name: Optional[str] = None
    ) -> Optional[FDALabelResponse]:
        """
        Search for drug label, trying brand name first, then generic name

        Args:
            brand_name: Brand name to search
            generic_name: Generic name for fallback

        Returns:
            FDALabelResponse or None if not found
        """
        # Try brand name first
        if brand_name:
            result = await self.search_by_brand_name(brand_name)
            if result:
                return result

        # Fallback to generic name
        if generic_name:
            result = await self.search_by_generic_name(generic_name)
            if result:
                return result

        logger.warning(f"No FDA label found for brand: {brand_name}, generic: {generic_name}")
        return None

    def _parse_label(self, label_data: dict) -> FDALabelResponse:
        """Parse FDA label JSON into structured response"""
        openfda = label_data.get("openfda", {})

        # Extract brand and generic names
        brand_names = openfda.get("brand_name", [])
        generic_names = openfda.get("generic_name", [])

        return FDALabelResponse(
            brand_name=brand_names[0] if brand_names else None,
            generic_name=generic_names[0] if generic_names else None,
            indications_and_usage=label_data.get("indications_and_usage", []),
            clinical_studies=label_data.get("clinical_studies", []),
            dosage_and_administration=label_data.get("dosage_and_administration", []),
            warnings=label_data.get("warnings", []),
            adverse_reactions=label_data.get("adverse_reactions", []),
            effective_time=label_data.get("effective_time"),
            raw_data=label_data
        )
