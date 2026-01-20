# 🌐 Streamlit Web Interface Guide

## Quick Start

### 1. Install & Configure

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
nano .env  # Add your ANTHROPIC_API_KEY
```

### 2. Launch Application

```bash
# Easy way
./run.sh

# Or manually
streamlit run streamlit_app.py
```

### 3. Access Web Interface

Open your browser to: **http://localhost:8501**

---

## 🎨 Interface Overview

### Main Screen

```
┌─────────────────────────────────────────────────────────────┐
│  💊 Drug Claims Retrieval System                           │
│  Generate MLR-ready pharmaceutical claims                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🔍 Enter Your Query                                        │
│  ┌─────────────────────────────────────────────┐           │
│  │ efficacy claims for Paxlovid in COVID-19   │ [Search]  │
│  └─────────────────────────────────────────────┘           │
│                                                             │
│  ⚙️ Advanced Options                                       │
│  [▼] Maximum claims: 6 | ☑ Save JSON output              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Sidebar Features

```
⚙️ Settings
├── API Configuration
│   ├── ✅ Claude API configured
│   └── ⚠️ NCBI API (optional)
│
├── 💡 Example Queries
│   ├── "efficacy claims for Paxlovid in COVID-19"
│   ├── "safety profile of Keytruda in melanoma"
│   └── "FDA-approved indications for Humira"
│
└── 📖 About
    └── System information
```

---

## 📊 Results Display

### 1. Search Summary

After processing, you'll see:

```
✅ Successfully generated 6 claims!

📊 Search Summary
┌────────────┬────────────┬────────────┬────────────┐
│ Search Time│ Claims     │ Full Text  │ Sources    │
│ 10.3s      │ 6          │ 6 articles │ 3          │
└────────────┴────────────┴────────────┴────────────┘

[📋 View Detailed Search Results ▼]
```

### 2. Claims Display

Each claim shows:

```
┌─────────────────────────────────────────────────┐
│ Claim #1                          [EFFICACY]    │
├─────────────────────────────────────────────────┤
│ 💊 Claim:                                       │
│ PAXLOVID reduced the risk of COVID-19-related  │
│ hospitalization or death by 89% compared to    │
│ placebo in high-risk adults.                   │
│                                                 │
│ Source: Peer Reviewed Full Text                │
│ Full Text: ✅ Yes                              │
│ Confidence: High - Full text substantiation    │
│                                                 │
│ [📄 View Substantiation ▼]                     │
│ [📚 View Citations (2) ▼]                      │
│ [🔢 Numerical Data ▼]                          │
└─────────────────────────────────────────────────┘
```

### 3. Expandable Sections

**Substantiation:**
```
📄 View Substantiation
┌─────────────────────────────────────────────────┐
│ In the EPIC-HR randomized, double-blind,       │
│ placebo-controlled trial (N=2,246), treatment  │
│ with nirmatrelvir 300mg/ritonavir 100mg twice  │
│ daily for 5 days within 3 days of symptom      │
│ onset resulted in COVID-19-related             │
│ hospitalization or death in 0.58% (6/1,039)    │
│ of patients compared to 5.73% (60/1,046)       │
│ receiving placebo...                           │
│                                                 │
│ Extracted from: Results section, paragraphs 3-5│
└─────────────────────────────────────────────────┘
```

**Citations:**
```
📚 View Citations (2)
┌─────────────────────────────────────────────────┐
│ Citation 1 (Primary)                            │
│ Hammond J, et al. Oral Nirmatrelvir for High-  │
│ Risk, Nonhospitalized Adults with Covid-19.    │
│ N Engl J Med. 2022;386(15):1397-1408          │
│                                                 │
│ - PMCID: PMC8908851                            │
│ - PMID: 35172054                               │
│ - DOI: 10.1056/NEJMoa2118542                   │
│ - [📖 View Full Text]                          │
│ ─────────────────────────────────────────────  │
│ Citation 2 (Supporting)                         │
│ EPIC-HR: Study of Oral PF-07321332/Ritonavir  │
│ - NCT: NCT04960202                             │
│ - [🔗 View Trial]                              │
└─────────────────────────────────────────────────┘
```

**Numerical Data:**
```
🔢 Numerical Data (for validation)
{
  "sample_size": 2246,
  "risk_reduction": "89%",
  "confidence_interval": "95% CI: 83%-93%",
  "p_value": "P<0.001",
  "time_frame": "28 days"
}
```

### 4. Excluded Articles

```
⚠️ Excluded Articles (No Full Text)
Found 14 relevant articles without full text in PMC

[View 14 excluded articles ▼]
```

### 5. Export Options

```
📥 Export Results
┌─────────────────┬─────────────────┐
│ ⬇️ Download JSON│ 📋 Copy JSON    │
└─────────────────┴─────────────────┘

💾 Results saved to: output/claims_20260120_120000.json
```

---

## 🎯 Key Features

### Real-Time Progress

Watch the system work:

```
📊 Processing...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 80%

🔎 Searching databases...

[📜 View Processing Logs ▼]
```

### Professional Logging

Click "View Processing Logs" to see:

```
┌──────────────────────────────────────────────┐
│ [12:00:00] INFO  PHASE 1: Intent Extraction  │
│ [12:00:01] INFO  Drug identified: Paxlovid   │
│ [12:00:02] INFO  PHASE 2-4: Parallel Search  │
│ [12:00:03] INFO  Searching OpenFDA...        │
│ [12:00:03] INFO  Searching PubMed/PMC...     │
│ [12:00:13] INFO  Search completed in 10.3s   │
│ [12:00:14] INFO  Found 6 full-text articles  │
│ [12:00:16] INFO  PHASE 6-8: Claims Generation│
│ [12:00:25] INFO  Generated 6 validated claims│
└──────────────────────────────────────────────┘
```

### JSON Export

Download results as JSON:

```json
{
  "search_summary": {...},
  "claims": [
    {
      "claim_id": 1,
      "claim_text": "...",
      "substantiation": "...",
      "citations": [...],
      "numerical_data": {...}
    }
  ],
  "additional_context": {...}
}
```

---

## 🔧 Advanced Options

### Settings Panel

```
⚙️ Advanced Options
├── Maximum claims to generate: [3-10] → 6
└── ☑ Save JSON output
```

**Options:**
- **Maximum claims**: Control how many claims to generate (3-10)
- **Save JSON**: Automatically save results to `output/` folder

---

## 💡 Usage Tips

### 1. Query Best Practices

**Good queries:**
- ✅ "efficacy claims for Paxlovid in COVID-19"
- ✅ "safety profile of Keytruda in melanoma patients"
- ✅ "dosing for Ozempic in type 2 diabetes"

**Avoid:**
- ❌ "Paxlovid" (too vague)
- ❌ "Tell me about COVID drugs" (not specific)
- ❌ "What is the best treatment?" (subjective)

### 2. Understanding Results

**Confidence Levels:**
- 🟢 **Highest - FDA Approved**: From FDA-approved labels
- 🟢 **High**: Full-text article with validated data
- 🟡 **Medium**: Full-text available but validation flagged issues

**Source Types:**
- 📘 **FDA_APPROVED_LABEL**: Most authoritative
- 📗 **PEER_REVIEWED_FULL_TEXT**: High quality with full text
- 📙 **CLINICAL_TRIAL_REGISTRY**: Supporting context

### 3. Reviewing Citations

**Click on links to:**
- View full articles in PubMed Central
- Check trial details on ClinicalTrials.gov
- Access FDA drug labels

### 4. Exporting Data

**Options:**
1. **Download JSON**: Save complete results
2. **Copy JSON**: Copy to clipboard for pasting
3. **Auto-save**: Enabled by default to `output/` folder

---

## 🚀 Performance

### Expected Timing

```
Phase 1: Intent Extraction        ~2s
Phase 2-4: Parallel Search        ~10s
Phase 5: Ranking & Filtering      ~2s
Phase 6-8: Claims Generation      ~8s
Phase 9: Quality Assurance        ~1s
Total                             ~23s
```

### Optimization Tips

- ✅ Keep queries specific
- ✅ Use recent drugs (more literature available)
- ✅ Specify population if relevant
- ✅ Adjust max claims based on needs

---

## 🐛 Troubleshooting

### "API key missing"

**Solution:**
```bash
cp .env.example .env
nano .env  # Add ANTHROPIC_API_KEY
```

### "No results found"

**Possible causes:**
- Drug name misspelled
- Very new drug (limited literature)
- Too specific query

**Try:**
- Check spelling
- Use brand name instead of generic (or vice versa)
- Broaden query scope

### "Full text not available"

**Explanation:**
- System found articles but they're paywalled
- Only ~30-40% of PubMed articles have free full text
- Check "Excluded Articles" section for details

### Performance issues

**If slow:**
- Check internet connection
- NCBI API key improves PubMed rate limits
- Large result sets take longer

---

## 📱 Mobile Support

The Streamlit interface is responsive and works on:
- ✅ Desktop (recommended)
- ✅ Tablet
- ✅ Mobile (limited)

---

## 🔒 Privacy & Security

- ✅ All processing happens on your machine
- ✅ API keys stored locally in `.env`
- ✅ No data sent to third parties (except API providers)
- ✅ Results saved locally only

---

## 🆘 Support

### Common Questions

**Q: Can I run multiple queries?**
A: Yes! Just enter a new query and click Search again.

**Q: Are results saved automatically?**
A: Yes, if "Save JSON output" is checked (default).

**Q: Can I access previous results?**
A: Yes, check the `output/` folder for saved JSON files.

**Q: How do I cite the system?**
A: Use the citations provided in each claim's output.

### Getting Help

1. Check logs in "View Processing Logs"
2. Review error messages
3. Check `.env` configuration
4. Verify API keys are valid

---

## 🎓 Next Steps

1. **Try example queries** from the sidebar
2. **Experiment** with different claim types
3. **Review** the JSON output structure
4. **Integrate** with your workflow

---

**Last Updated:** January 20, 2026
**Version:** 2.0.0 (Streamlit)
**Status:** ✅ Production Ready
