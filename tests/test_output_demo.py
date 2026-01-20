"""
Output structure demonstration test
Shows the expected JSON output format without requiring API calls
"""
import json
from datetime import datetime
from src.models.claim import (
    Claim,
    Citation,
    CitationType,
    SourceType,
    ClaimsOutput,
    SearchSummary,
    ArticleWithoutFullText
)


def test_output_structure():
    """
    Demonstrate the complete output structure
    This test creates a mock output to show what the system produces
    """

    # Create a sample FDA citation
    fda_citation = Citation(
        primary=True,
        citation_type=CitationType.FDA_LABEL,
        text="PAXLOVID (nirmatrelvir tablets; ritonavir tablets) Prescribing Information. Pfizer Inc. Revised December 2024.",
        section="Indications and Usage",
        url="https://www.accessdata.fda.gov/scripts/cder/daf/"
    )

    # Create a sample journal citation
    journal_citation = Citation(
        primary=True,
        citation_type=CitationType.JOURNAL_ARTICLE,
        authors="Hammond J, Leister-Tebbe H, Gardner A, et al.",
        title="Oral Nirmatrelvir for High-Risk, Nonhospitalized Adults with Covid-19",
        journal="N Engl J Med",
        year=2022,
        volume="386",
        issue="15",
        pages="1397-1408",
        pmid="35172054",
        pmcid="PMC8908851",
        doi="10.1056/NEJMoa2118542",
        pmc_url="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8908851/",
        full_text_available=True
    )

    # Create a trial registry citation
    trial_citation = Citation(
        primary=False,
        citation_type=CitationType.TRIAL_REGISTRY,
        text="EPIC-HR: Study of Oral PF-07321332/Ritonavir Compared With Placebo",
        nct="NCT04960202",
        url="https://clinicaltrials.gov/study/NCT04960202"
    )

    # Create sample FDA claim
    fda_claim = Claim(
        claim_id=1,
        claim_type="indication",
        claim_text="PAXLOVID is indicated for the treatment of mild-to-moderate COVID-19 in adults and pediatric patients (12 years of age and older weighing at least 40 kg) with positive results of direct SARS-CoV-2 testing, and who are at high risk for progression to severe COVID-19.",
        substantiation="PAXLOVID is a co-packaged product containing nirmatrelvir tablets and ritonavir tablets. It is indicated for the treatment of coronavirus disease 2019 (COVID-19) in adults and pediatric patients who meet the specified criteria.",
        source_type=SourceType.FDA_APPROVED_LABEL,
        citations=[fda_citation],
        confidence="Highest - FDA Approved",
        full_text_used=True,
        extracted_from="FDA Label - Indications and Usage"
    )

    # Create sample efficacy claim from full text
    efficacy_claim = Claim(
        claim_id=2,
        claim_type="efficacy",
        claim_text="PAXLOVID reduced the risk of COVID-19-related hospitalization or death by 89% compared to placebo in high-risk adults.",
        substantiation=(
            "In the EPIC-HR randomized, double-blind, placebo-controlled trial (N=2,246), "
            "treatment with nirmatrelvir 300mg/ritonavir 100mg twice daily for 5 days within "
            "3 days of symptom onset resulted in COVID-19-related hospitalization or death in "
            "0.58% (6/1,039) of patients compared to 5.73% (60/1,046) receiving placebo, "
            "representing an 89% relative risk reduction (95% CI: 83%-93%, P<0.001) through "
            "28 days of follow-up."
        ),
        source_type=SourceType.PEER_REVIEWED_FULL_TEXT,
        citations=[journal_citation, trial_citation],
        confidence="High - Full text substantiation with validated data",
        full_text_used=True,
        extracted_from="Results section, paragraphs 3-5",
        numerical_data={
            "sample_size": 2246,
            "treatment_group": "6/1039 (0.58%)",
            "control_group": "60/1046 (5.73%)",
            "risk_reduction": "89%",
            "confidence_interval": "95% CI: 83%-93%",
            "p_value": "P<0.001",
            "time_frame": "28 days"
        }
    )

    # Create search summary
    search_summary = SearchSummary(
        user_query="efficacy claims for Paxlovid in COVID-19 for high-risk patients",
        sources_searched=["OpenFDA", "PubMed/PMC", "ClinicalTrials.gov"],
        results_found={
            "fda_labels": 1,
            "pubmed_total": 20,
            "pubmed_full_text": 6,
            "pubmed_abstract_only": 14,
            "clinical_trials": 3
        },
        full_text_strategy="Claims generated only from full-text articles (PMC)",
        search_time_seconds=10.3,
        timestamp=datetime.now()
    )

    # Create excluded article example
    excluded_article = ArticleWithoutFullText(
        pmid="34567890",
        title="Real-world effectiveness of Paxlovid in preventing severe COVID-19 outcomes",
        journal="The Lancet",
        year=2023,
        authors="Smith J, et al.",
        note="Relevant but full text not available in PMC - paywalled",
        doi="10.1016/S0140-6736(23)01234-5"
    )

    # Create complete output
    output = ClaimsOutput(
        search_summary=search_summary,
        claims=[fda_claim, efficacy_claim],
        additional_context={
            "articles_without_full_text": [excluded_article],
            "recommendation": (
                "2 claims generated from full-text sources (1 FDA label + 1 peer-reviewed article). "
                "14 additional relevant articles identified but excluded due to lack of full text access."
            )
        }
    )

    # Convert to JSON
    output_json = output.model_dump(mode="json")

    # Save to file for inspection
    with open("tests/sample_output.json", "w") as f:
        json.dump(output_json, f, indent=2, default=str)

    # Assertions
    assert output.search_summary.user_query == "efficacy claims for Paxlovid in COVID-19 for high-risk patients"
    assert len(output.claims) == 2
    assert output.claims[0].source_type == SourceType.FDA_APPROVED_LABEL
    assert output.claims[1].source_type == SourceType.PEER_REVIEWED_FULL_TEXT
    assert output.claims[1].full_text_used is True
    assert "sample_size" in output.claims[1].numerical_data
    assert output.search_summary.results_found["pubmed_full_text"] == 6

    print("\n" + "=" * 80)
    print("SAMPLE OUTPUT STRUCTURE")
    print("=" * 80)
    print("\nSearch Summary:")
    print(f"  Query: {output.search_summary.user_query}")
    print(f"  Sources: {', '.join(output.search_summary.sources_searched)}")
    print(f"  Results found:")
    print(f"    - FDA Labels: {output.search_summary.results_found['fda_labels']}")
    print(f"    - PubMed Total: {output.search_summary.results_found['pubmed_total']}")
    print(f"    - PubMed Full Text: {output.search_summary.results_found['pubmed_full_text']}")
    print(f"    - PubMed Abstract Only: {output.search_summary.results_found['pubmed_abstract_only']}")
    print(f"  Search Time: {output.search_summary.search_time_seconds}s")

    print(f"\nGenerated Claims: {len(output.claims)}")
    for claim in output.claims:
        print(f"\n  Claim #{claim.claim_id} ({claim.claim_type}):")
        print(f"    Source: {claim.source_type}")
        print(f"    Confidence: {claim.confidence}")
        print(f"    Full Text Used: {claim.full_text_used}")
        print(f"    Citations: {len(claim.citations)}")
        print(f"    Text: {claim.claim_text[:100]}...")

    print(f"\nExcluded Articles (no full text): {len(output.additional_context['articles_without_full_text'])}")
    print(f"\n{output.additional_context['recommendation']}")

    print("\n" + "=" * 80)
    print(f"Full JSON output saved to: tests/sample_output.json")
    print("=" * 80)

    return True


if __name__ == "__main__":
    test_output_structure()
