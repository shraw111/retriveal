# Drug Claims Retrieval System

A comprehensive system for retrieving and generating MLR-ready pharmaceutical claims from FDA labels, peer-reviewed literature, and clinical trial registries.

## Features

✅ **Multi-Source Search**: Parallel search across OpenFDA, PubMed/PMC, and ClinicalTrials.gov
✅ **Full-Text Analysis**: Claims generated only from complete articles (not abstracts)
✅ **LLM-Powered Extraction**: Uses Claude API for intelligent intent parsing and claim generation
✅ **Quality Assurance**: Automated validation of numerical accuracy and data integrity
✅ **MLR-Ready Output**: Professional citations and substantiation for regulatory review
✅ **Fast Execution**: ~10 seconds end-to-end with parallel processing

## Architecture

```
User Query (Free Text)
    ↓
┌─────────────────────────────────────┐
│ PHASE 1: Intent Extraction          │
│ - Parse query with Claude API        │
│ - Identify drug, indication, claim type │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ PHASE 2-4: Parallel Search          │
│ ┌─────────┬──────────┬────────────┐ │
│ │ OpenFDA │ PubMed   │ Clinical   │ │
│ │ Label   │ Full Text│ Trials     │ │
│ └─────────┴──────────┴────────────┘ │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ PHASE 5: Ranking & Filtering        │
│ - Keep only full-text articles      │
│ - Score relevance with LLM           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ PHASE 6-8: Claims Generation        │
│ - Extract from FDA label             │
│ - Extract from full-text Results    │
│ - Format citations                   │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ PHASE 9: Quality Assurance           │
│ - Validate numerical accuracy        │
│ - Check completeness                 │
└─────────────────────────────────────┘
    ↓
Structured JSON Output
```

## Installation

### Prerequisites

- Python 3.11 or higher
- Anthropic API key (for Claude)
- NCBI API key (optional but recommended)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd retriveal
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

   Required variables:
   ```
   ANTHROPIC_API_KEY=your_claude_api_key_here
   ```

   Optional variables:
   ```
   NCBI_API_KEY=your_ncbi_api_key_here
   NCBI_EMAIL=your_email@example.com
   LOG_LEVEL=INFO
   MAX_RESULTS_PUBMED=20
   MAX_RESULTS_CLINICAL_TRIALS=10
   ```

## Usage

### Command Line Interface

Basic usage:
```bash
python -m src.main "efficacy claims for Paxlovid in treating COVID-19 in high-risk patients"
```

Save to specific file:
```bash
python -m src.main "safety claims for Keytruda in melanoma" output/keytruda_claims.json
```

### Python API

```python
import asyncio
from src.main import DrugClaimsRetrieval

async def main():
    # Initialize system
    system = DrugClaimsRetrieval()

    # Process query
    result = await system.process_query(
        "efficacy claims for Paxlovid in COVID-19"
    )

    # Access results
    print(f"Generated {len(result.claims)} claims")
    for claim in result.claims:
        print(f"\nClaim #{claim.claim_id}:")
        print(f"  {claim.claim_text}")
        print(f"  Confidence: {claim.confidence}")
        print(f"  Citations: {len(claim.citations)}")

asyncio.run(main())
```

### Example Queries

```bash
# Efficacy claims
python -m src.main "efficacy claims for Paxlovid in treating COVID-19"

# Safety profile
python -m src.main "safety profile for Ozempic in type 2 diabetes"

# Indication claims
python -m src.main "approved indications for Humira"

# Specific population
python -m src.main "efficacy of Eliquis in elderly patients with atrial fibrillation"

# Dosing information
python -m src.main "dosing recommendations for Keytruda in melanoma"
```

## Output Format

The system returns structured JSON with:

```json
{
  "search_summary": {
    "user_query": "original query",
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
  "claims": [
    {
      "claim_id": 1,
      "claim_type": "efficacy",
      "claim_text": "Concise MLR-ready claim statement",
      "substantiation": "Detailed paragraph with study design, results, statistics...",
      "source_type": "FDA_APPROVED_LABEL",
      "citations": [
        {
          "primary": true,
          "citation_type": "FDA_LABEL",
          "text": "PAXLOVID PI, December 2024"
        }
      ],
      "confidence": "Highest - FDA Approved",
      "full_text_used": true
    }
  ],
  "additional_context": {
    "articles_without_full_text": [
      {
        "pmid": "12345678",
        "title": "Relevant article title",
        "note": "Full text not available in PMC - paywalled"
      }
    ],
    "recommendation": "6 claims generated from full-text sources..."
  }
}
```

## Key Features Explained

### 3-Step PubMed Full-Text Retrieval

The system uses a sophisticated 3-step process to retrieve complete articles:

1. **Search**: Query PubMed to get PMIDs
2. **Metadata**: Fetch article details to find PMC IDs
3. **Full Text**: Download complete articles from PubMed Central

**Critical**: Only ~30-40% of PubMed articles have full text in PMC. The system automatically filters out articles without full text to ensure high-quality claims.

### Full-Text Only Strategy

Claims are **only** generated from complete articles, never from abstracts alone:

- ✅ FDA labels (pre-approved)
- ✅ Full-text articles from PubMed Central
- ❌ Abstract-only articles (excluded)

This ensures all claims can be fully substantiated with complete data.

### Quality Assurance

Automated validation includes:

- **Numerical accuracy**: All numbers in claims exactly match source text
- **Completeness**: Required fields present and adequate length
- **Citation integrity**: All citations have required identifiers
- **Full-text verification**: Claims marked with source type and availability

### Parallel Execution

All 3 data sources are queried simultaneously:

- OpenFDA: ~2-3 seconds
- PubMed (3 steps): ~8-10 seconds
- ClinicalTrials.gov: ~2-3 seconds

**Total time**: ~10 seconds (limited by slowest source)

## Data Sources

### OpenFDA
- **Purpose**: FDA-approved drug labels
- **Authority**: Highest (gold standard)
- **API**: https://open.fda.gov/apis/drug/label/
- **Usage**: No API key required

### PubMed/PMC
- **Purpose**: Peer-reviewed clinical trials
- **Authority**: High (Phase 3 RCTs in top journals)
- **API**: NCBI E-utilities
- **Usage**: API key optional but recommended for higher rate limits

### ClinicalTrials.gov
- **Purpose**: Trial registration and results
- **Authority**: Medium (context and verification)
- **API**: https://clinicaltrials.gov/api/v2/
- **Usage**: No API key required

## Development

### Project Structure

```
retriveal/
├── src/
│   ├── models/              # Data models
│   │   ├── intent.py        # User intent structures
│   │   ├── claim.py         # Claim and citation models
│   │   └── api_responses.py # API response models
│   ├── api/                 # API clients
│   │   ├── openfda.py       # OpenFDA client
│   │   ├── pubmed.py        # PubMed/PMC client (3-step)
│   │   └── clinicaltrials.py # ClinicalTrials.gov client
│   ├── processors/          # Core processing logic
│   │   ├── intent_parser.py      # Phase 1: Intent extraction
│   │   ├── search_orchestrator.py # Phase 2-4: Parallel search
│   │   ├── ranker.py             # Phase 5: Ranking
│   │   └── claims_generator.py   # Phase 6-8: Claims generation
│   ├── utils/               # Utilities
│   │   ├── llm_client.py    # Claude API integration
│   │   └── validators.py    # Quality assurance
│   └── main.py              # Main application
├── tests/                   # Unit tests
├── examples/                # Example scripts
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_basic.py::test_user_intent_model -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking (if you add type hints)
mypy src/
```

## Troubleshooting

### Common Issues

**1. No API key error**
```
ValueError: ANTHROPIC_API_KEY not found
```
Solution: Create `.env` file and add your Claude API key

**2. No full-text articles found**
```
WARNING: No full text available for 15 PubMed articles
```
This is expected - most recent articles are paywalled. The system works correctly by excluding them.

**3. Rate limiting**
```
HTTPError: 429 Too Many Requests
```
Solution: Add NCBI API key to `.env` for higher rate limits

**4. Timeout errors**
```
asyncio.TimeoutError
```
Solution: Increase timeout in .env or check network connection

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG python -m src.main "your query"
```

## Performance

Typical performance metrics:

- **Search time**: 8-12 seconds
- **Total pipeline**: 15-25 seconds (including LLM processing)
- **API calls**:
  - OpenFDA: 1-2 calls
  - PubMed: 3 calls (search + metadata + full text)
  - ClinicalTrials.gov: 1 call
  - Claude API: 3-8 calls (intent + relevance scoring + claims extraction)

## Limitations

1. **Full-text availability**: Only ~30-40% of PubMed articles have free full text in PMC
2. **Recency**: Very recent articles (last 1-2 months) may not have full text yet
3. **Language**: English-only articles
4. **LLM costs**: Claude API calls incur costs (~$0.10-0.50 per query depending on results)

## Future Enhancements

- [ ] Add support for institutional full-text access (Unpaywall, Europe PMC)
- [ ] Implement caching for repeated queries
- [ ] Add batch processing mode
- [ ] Support for multiple languages
- [ ] Integration with reference management tools
- [ ] Web interface

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Add your license here]

## Citation

If you use this system in your research, please cite:

```
[Add citation information]
```

## Support

For issues and questions:
- GitHub Issues: [repository]/issues
- Email: [your email]

## Acknowledgments

- OpenFDA for providing free access to FDA drug labels
- NCBI for PubMed and PubMed Central APIs
- ClinicalTrials.gov for clinical trial data
- Anthropic for Claude API

---

Built with ❤️ for pharmaceutical medical affairs teams
