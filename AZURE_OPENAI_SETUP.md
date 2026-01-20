# 🔷 Azure OpenAI Setup Guide

## Quick Start for Azure OpenAI

The system now supports **Azure OpenAI** as the primary LLM provider (instead of Anthropic Claude).

---

## 📋 Prerequisites

1. **Azure Subscription** with access to Azure OpenAI Service
2. **Azure OpenAI Resource** deployed
3. **GPT-4 Deployment** created in your Azure OpenAI resource

---

## 🚀 Setup Steps

### Step 1: Get Your Azure OpenAI Credentials

1. **Go to Azure Portal** → Azure OpenAI Service
2. **Select your resource**
3. **Navigate to "Keys and Endpoint"**
4. **Copy these values:**
   - **Key 1** (API Key)
   - **Endpoint** (e.g., `https://your-resource.openai.azure.com/`)

5. **Navigate to "Model deployments"**
6. **Note your deployment name** (e.g., `gpt-4`, `gpt-4-32k`, `gpt-35-turbo`)

### Step 2: Configure .env File

```bash
# Copy the template
cp .env.example .env

# Edit .env file
nano .env
```

**Add your Azure OpenAI credentials:**

```bash
# LLM Provider Selection
LLM_PROVIDER=azure  # IMPORTANT: Set to "azure"

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_actual_api_key_from_step_1
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4  # Your deployment name
AZURE_OPENAI_API_VERSION=2024-02-15-preview  # Usually this works

# Leave Anthropic commented out
# ANTHROPIC_API_KEY=not_needed_for_azure
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `openai==1.12.0` - Azure OpenAI SDK
- All other required packages

### Step 4: Test Configuration

```bash
# Launch Streamlit
./run.sh

# Or manually
streamlit run streamlit_app.py
```

**You should see:**
```
INFO - Using LLM provider: azure
INFO - Initialized Azure OpenAI client with deployment: gpt-4
INFO - Initialization complete
```

---

## 🎯 Example Configuration

### Your .env File Should Look Like This:

```bash
# LLM API Configuration
LLM_PROVIDER=azure

# Azure OpenAI Settings
AZURE_OPENAI_API_KEY=abc123def456ghi789jkl012mno345pqr678
AZURE_OPENAI_ENDPOINT=https://mycompany-openai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# NCBI (Optional but recommended)
# NCBI_API_KEY=your_ncbi_key
# NCBI_EMAIL=your@email.com

# Application Settings
LOG_LEVEL=INFO
MAX_RESULTS_PUBMED=20
MAX_RESULTS_CLINICAL_TRIALS=10
```

---

## 🔧 Recommended Azure OpenAI Deployments

### For Best Results:

| Model | Deployment Name | Use Case | Cost |
|-------|----------------|----------|------|
| **GPT-4** | `gpt-4` | **Recommended** - Best accuracy for medical claims | $$$ |
| **GPT-4-32k** | `gpt-4-32k` | For very long articles (if needed) | $$$$ |
| **GPT-3.5-Turbo** | `gpt-35-turbo` | Budget option (may reduce accuracy) | $ |

**Recommendation:** Use **GPT-4** for pharmaceutical claims extraction to ensure accuracy.

---

## 💰 Cost Estimation

### Azure OpenAI Pricing (approximate):

**GPT-4 Pricing:**
- Input: $0.03 per 1K tokens
- Output: $0.06 per 1K tokens

**Per Query Estimate:**
- Intent extraction: ~500 tokens in + 200 tokens out = $0.03
- Relevance scoring (6 articles): ~3K tokens in + 60 tokens out = $0.10
- Claims generation (6 claims): ~15K tokens in + 6K tokens out = $0.81

**Total per query: ~$0.94**

**Note:** Costs may vary based on:
- Deployment region
- Contract pricing
- Token usage

---

## 🔄 Switching Between Providers

### Use Azure OpenAI:
```bash
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### Use Anthropic Claude:
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_key
```

**Just change `LLM_PROVIDER` and restart!**

---

## 🧪 Testing Your Setup

### Test 1: Basic Query

```bash
# Launch Streamlit
./run.sh
```

**In the web interface, try:**
```
Paxlovid covid 19 efficacy for HCPs
```

**Expected:**
- Progress bar shows phases
- Logs show "Using LLM provider: azure"
- Claims generated successfully
- No errors about API keys

### Test 2: CLI Test

```bash
python -m src.main "efficacy claims for aspirin"
```

**Expected output:**
```
INFO - Using LLM provider: azure
INFO - Initialized Azure OpenAI client with deployment: gpt-4
INFO - PHASE 1: Intent Extraction
...
SUCCESS!
```

---

## 🐛 Troubleshooting

### Error: "Azure OpenAI configuration missing"

**Solution:**
```bash
# Check your .env file has all required fields:
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your_key  # Must be set
AZURE_OPENAI_ENDPOINT=your_endpoint  # Must be set
AZURE_OPENAI_DEPLOYMENT=gpt-4  # Optional, defaults to gpt-4
```

### Error: "Authentication failed"

**Possible causes:**
1. **Wrong API key** - Copy from Azure Portal again
2. **Key expired** - Regenerate in Azure Portal
3. **Wrong endpoint** - Should end with `.openai.azure.com/`
4. **Resource not active** - Check Azure Portal

**Solution:**
- Verify credentials in Azure Portal
- Regenerate keys if needed
- Ensure endpoint URL is correct

### Error: "Deployment not found"

**Cause:** Deployment name doesn't match Azure

**Solution:**
```bash
# Check Azure Portal → Model deployments → Copy exact name
AZURE_OPENAI_DEPLOYMENT=gpt-4  # Must match exactly
```

### Error: "Rate limit exceeded"

**Cause:** Too many requests

**Solution:**
- Azure OpenAI has rate limits (Tokens Per Minute)
- Check your quota in Azure Portal
- Consider upgrading your quota
- Add delays between requests if needed

---

## 📊 Comparison: Azure OpenAI vs Anthropic Claude

| Feature | Azure OpenAI (GPT-4) | Anthropic Claude |
|---------|---------------------|------------------|
| **Cost per Query** | ~$0.94 | ~$0.10 |
| **Medical Accuracy** | ✅ Excellent | ✅ Excellent |
| **Enterprise Support** | ✅ Azure enterprise | ❌ Direct API only |
| **Data Privacy** | ✅ Your Azure tenant | ⚠️ Anthropic servers |
| **Compliance** | ✅ HIPAA/SOC2/ISO via Azure | ✅ SOC2 |
| **Customization** | ⚠️ Limited | ✅ Better prompt following |
| **Best For** | Enterprise/corporate | Startups/individual |

**For HCPs/Pharma:** Azure OpenAI is often preferred for:
- Enterprise compliance requirements
- Data residency needs
- Existing Azure infrastructure
- Corporate IT policies

---

## 🎯 Performance Tuning

### Adjust Temperature (if needed):

Edit `src/utils/azure_openai_client.py`:

```python
# For more deterministic output
temperature=0  # Current setting (recommended)

# For more creative output (not recommended for medical)
temperature=0.7
```

### Adjust Max Tokens:

```python
# Intent extraction
max_tokens=1024  # Current (sufficient)

# Claims generation
max_tokens=2048  # Current (good for detailed claims)
```

---

## 📝 What Gets Sent to Azure OpenAI

**Data sent:**
1. User query (e.g., "efficacy claims for Paxlovid")
2. FDA label text (public data)
3. PubMed article results sections (public data)
4. Structured prompts for extraction

**Data NOT sent:**
- Your API keys
- Patient data (system doesn't handle PHI)
- Proprietary information

**All data is processed according to Azure's data handling policies.**

---

## ✅ Verification Checklist

Before going to production:

- [ ] `.env` file configured with Azure credentials
- [ ] `LLM_PROVIDER=azure` set correctly
- [ ] Tested with sample query
- [ ] No authentication errors
- [ ] Claims generating successfully
- [ ] Logs show "Using LLM provider: azure"
- [ ] Rate limits understood
- [ ] Cost budget allocated
- [ ] Data privacy reviewed
- [ ] Compliance requirements met

---

## 🆘 Getting Help

### Azure OpenAI Issues:
- **Azure Portal** → Support → New support request
- **Azure OpenAI Documentation:** https://learn.microsoft.com/en-us/azure/ai-services/openai/

### Application Issues:
- Check logs in Streamlit interface
- Verify `.env` configuration
- Test with simple query first
- Check `output/` folder for saved results

---

## 🚀 You're Ready!

Your system is now configured to use **Azure OpenAI** for pharmaceutical claims extraction.

**Next steps:**
1. Test with your Paxlovid query
2. Review the generated claims
3. Validate accuracy
4. Adjust max_claims if needed
5. Export results as JSON

**Example query to try:**
```
Paxlovid covid 19 efficacy for HCPs
```

**Expected result:** 6 MLR-ready claims with full substantiation and citations from FDA labels and peer-reviewed full-text articles.

---

**Last Updated:** January 20, 2026
**Version:** 2.1.0 (Azure OpenAI Support)
**Status:** ✅ Production Ready with Azure OpenAI
