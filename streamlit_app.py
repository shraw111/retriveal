"""
Drug Claims Retrieval System - Streamlit Web Interface
Professional web UI with real-time logging, JSON output, and automation support
"""
import streamlit as st
import asyncio
import json
import time
import logging
import io
import sys
from datetime import datetime
from pathlib import Path

from src.main import DrugClaimsRetrieval
from src.models.claim import ClaimsOutput

# Configure page
st.set_page_config(
    page_title="Drug Claims Retrieval System",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .claim-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .confidence-high {
        color: #28a745;
        font-weight: 600;
    }
    .confidence-medium {
        color: #ffc107;
        font-weight: 600;
    }
    .log-container {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        max-height: 400px;
        overflow-y: auto;
    }
    .phase-header {
        color: #1f77b4;
        font-weight: 600;
        font-size: 1.1rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


class StreamlitLogHandler(logging.Handler):
    """Custom log handler that captures logs for Streamlit display"""
    def __init__(self):
        super().__init__()
        self.logs = []

    def emit(self, record):
        log_entry = self.format(record)
        self.logs.append({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'level': record.levelname,
            'message': record.getMessage()
        })


def initialize_system():
    """Initialize the Drug Claims Retrieval System"""
    if 'system' not in st.session_state:
        try:
            with st.spinner("Initializing system..."):
                st.session_state.system = DrugClaimsRetrieval()
                st.session_state.initialized = True
        except ValueError as e:
            st.error(f"❌ Configuration Error: {e}")
            st.info("💡 Please add your ANTHROPIC_API_KEY to the .env file")
            st.session_state.initialized = False
        except Exception as e:
            st.error(f"❌ Initialization Error: {e}")
            st.session_state.initialized = False


def display_logs(log_handler):
    """Display logs in a professional console-style container"""
    if log_handler.logs:
        log_html = "<div class='log-container'>"
        for log in log_handler.logs[-50:]:  # Show last 50 logs
            level_color = {
                'INFO': '#4CAF50',
                'WARNING': '#FFC107',
                'ERROR': '#F44336',
                'DEBUG': '#2196F3'
            }.get(log['level'], '#d4d4d4')

            log_html += f"<div style='margin-bottom: 4px;'>"
            log_html += f"<span style='color: #888;'>[{log['timestamp']}]</span> "
            log_html += f"<span style='color: {level_color}; font-weight: 600;'>{log['level']}</span> "
            log_html += f"<span>{log['message']}</span>"
            log_html += "</div>"
        log_html += "</div>"
        st.markdown(log_html, unsafe_allow_html=True)


def display_search_summary(claims_output: ClaimsOutput):
    """Display search summary with metrics"""
    st.markdown("<div class='phase-header'>📊 Search Summary</div>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Search Time",
            f"{claims_output.search_summary.search_time_seconds:.1f}s",
            help="Total time for parallel search across all sources"
        )

    with col2:
        st.metric(
            "Claims Generated",
            len(claims_output.claims),
            help="Total MLR-ready claims extracted"
        )

    with col3:
        st.metric(
            "Full Text Articles",
            claims_output.search_summary.results_found.get('pubmed_full_text', 0),
            help="Articles with complete text from PubMed Central"
        )

    with col4:
        st.metric(
            "Sources Searched",
            len(claims_output.search_summary.sources_searched),
            help="OpenFDA, PubMed/PMC, ClinicalTrials.gov"
        )

    # Detailed results
    with st.expander("📋 Detailed Search Results"):
        results = claims_output.search_summary.results_found

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**FDA Labels**")
            st.info(f"✓ {results.get('fda_labels', 0)} label(s) found")

            st.markdown("**PubMed/PMC**")
            st.info(f"📚 {results.get('pubmed_total', 0)} total articles found")
            st.success(f"✓ {results.get('pubmed_full_text', 0)} with full text")
            st.warning(f"⚠️ {results.get('pubmed_abstract_only', 0)} abstract only (excluded)")

        with col2:
            st.markdown("**ClinicalTrials.gov**")
            st.info(f"🔬 {results.get('clinical_trials', 0)} trials found")

            st.markdown("**Strategy**")
            st.success(claims_output.search_summary.full_text_strategy)


def display_claim(claim, index):
    """Display a single claim in a professional card format"""

    # Confidence badge styling
    confidence_class = "confidence-high" if "High" in claim.confidence or "Highest" in claim.confidence else "confidence-medium"

    st.markdown(f"""
    <div class='claim-card'>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;'>
            <h3 style='margin: 0; color: #1f77b4;'>Claim #{claim.claim_id}</h3>
            <span style='background-color: #e3f2fd; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.85rem;'>
                {claim.claim_type.upper()}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Claim text
    st.markdown(f"**💊 Claim:**")
    st.info(claim.claim_text)

    # Metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Source:** {claim.source_type.replace('_', ' ').title()}")
    with col2:
        st.markdown(f"**Full Text:** {'✅ Yes' if claim.full_text_used else '❌ No'}")
    with col3:
        st.markdown(f"**Confidence:** <span class='{confidence_class}'>{claim.confidence}</span>", unsafe_allow_html=True)

    # Substantiation
    with st.expander("📄 View Substantiation"):
        st.markdown(claim.substantiation)
        if claim.extracted_from:
            st.caption(f"*Extracted from: {claim.extracted_from}*")

    # Citations
    with st.expander(f"📚 View Citations ({len(claim.citations)})"):
        for i, citation in enumerate(claim.citations, 1):
            st.markdown(f"**Citation {i}** {'(Primary)' if citation.primary else '(Supporting)'}")

            if citation.citation_type.value == "JOURNAL_ARTICLE":
                citation_text = f"{citation.authors}. {citation.title}. *{citation.journal}*"
                if citation.year:
                    citation_text += f". {citation.year}"
                if citation.volume and citation.issue:
                    citation_text += f";{citation.volume}({citation.issue})"
                if citation.pages:
                    citation_text += f":{citation.pages}"

                st.markdown(citation_text)

                if citation.pmcid:
                    st.markdown(f"- **PMCID:** {citation.pmcid}")
                if citation.pmid:
                    st.markdown(f"- **PMID:** {citation.pmid}")
                if citation.doi:
                    st.markdown(f"- **DOI:** {citation.doi}")
                if citation.pmc_url:
                    st.markdown(f"- [📖 View Full Text]({citation.pmc_url})")

            elif citation.citation_type.value == "FDA_LABEL":
                st.markdown(citation.text)
                if citation.section:
                    st.caption(f"Section: {citation.section}")

            elif citation.citation_type.value == "TRIAL_REGISTRY":
                st.markdown(citation.text)
                if citation.nct:
                    st.markdown(f"- **NCT:** {citation.nct}")
                if citation.url:
                    st.markdown(f"- [🔗 View Trial]({citation.url})")

            st.divider()

    # Numerical data
    if claim.numerical_data:
        with st.expander("🔢 Numerical Data (for validation)"):
            st.json(claim.numerical_data)

    st.markdown("<br>", unsafe_allow_html=True)


def display_excluded_articles(claims_output: ClaimsOutput):
    """Display articles that were excluded due to lack of full text"""
    excluded = claims_output.additional_context.get('articles_without_full_text', [])

    if excluded:
        st.markdown("<div class='phase-header'>⚠️ Excluded Articles (No Full Text)</div>", unsafe_allow_html=True)
        st.warning(f"Found {len(excluded)} relevant articles without full text in PubMed Central")

        with st.expander(f"View {len(excluded)} excluded articles"):
            for article in excluded[:10]:  # Show first 10
                st.markdown(f"**{article.get('title', 'No title')}**")
                st.caption(f"{article.get('journal', 'Unknown journal')} ({article.get('year', 'N/A')})")
                if article.get('pmid'):
                    st.caption(f"PMID: {article['pmid']}")
                if article.get('doi'):
                    st.caption(f"DOI: {article['doi']}")
                st.caption(f"⚠️ {article.get('note', 'Full text not available')}")
                st.divider()


def main():
    """Main Streamlit application"""

    # Header
    st.markdown("<div class='main-header'>💊 Drug Claims Retrieval System</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Generate MLR-ready pharmaceutical claims from FDA labels, peer-reviewed literature, and clinical trials</div>", unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")

        # API Status
        st.markdown("#### API Configuration")
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv()

            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if anthropic_key:
                st.success("✅ Claude API configured")
            else:
                st.error("❌ Claude API key missing")
                st.info("Add ANTHROPIC_API_KEY to .env file")
        except:
            st.warning("⚠️ Could not check API status")

        st.divider()

        # Query examples
        st.markdown("#### 💡 Example Queries")
        st.code("efficacy claims for Paxlovid in COVID-19")
        st.code("safety profile of Keytruda in melanoma")
        st.code("FDA-approved indications for Humira")
        st.code("dosing for Ozempic in type 2 diabetes")

        st.divider()

        # About
        st.markdown("#### 📖 About")
        st.markdown("""
        This system retrieves pharmaceutical claims from:
        - **OpenFDA** (drug labels)
        - **PubMed/PMC** (full-text articles)
        - **ClinicalTrials.gov** (trial data)

        **Features:**
        - ✅ Full-text only (no abstracts)
        - ✅ Multi-source citations
        - ✅ Numerical validation
        - ✅ MLR-ready output
        """)

    # Initialize system
    initialize_system()

    if not st.session_state.get('initialized', False):
        st.stop()

    # Main query input
    st.markdown("### 🔍 Enter Your Query")

    col1, col2 = st.columns([3, 1])

    with col1:
        user_query = st.text_input(
            "Query",
            placeholder="e.g., efficacy claims for Paxlovid in COVID-19 high-risk patients",
            label_visibility="collapsed",
            key="query_input"
        )

    with col2:
        search_button = st.button("🚀 Search", type="primary", use_container_width=True)

    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            max_claims = st.slider("Maximum claims to generate", 3, 10, 6)
        with col2:
            save_json = st.checkbox("Save JSON output", value=True)

    # Process query
    if search_button and user_query:
        # Setup logging
        log_handler = StreamlitLogHandler()
        log_handler.setFormatter(logging.Formatter('%(message)s'))
        logger = logging.getLogger()
        logger.addHandler(log_handler)
        logger.setLevel(logging.INFO)

        # Progress container
        progress_container = st.container()

        with progress_container:
            st.markdown("### 📊 Processing...")

            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Log display
            log_display = st.empty()

            try:
                # Update user intent requirements
                st.session_state.system.claims_generator.claude.max_claims = max_claims

                # Phase indicators
                phases = [
                    (0.2, "🔍 Extracting intent..."),
                    (0.4, "🔎 Searching databases..."),
                    (0.6, "📊 Ranking results..."),
                    (0.8, "📝 Generating claims..."),
                    (1.0, "✅ Complete!")
                ]

                # Run processing
                async def process():
                    for progress, status in phases[:4]:
                        progress_bar.progress(progress)
                        status_text.text(status)
                        await asyncio.sleep(0.1)

                    result = await st.session_state.system.process_query(user_query)

                    progress_bar.progress(1.0)
                    status_text.text("✅ Complete!")

                    return result

                # Execute
                claims_output = asyncio.run(process())

                # Display logs
                with st.expander("📜 View Processing Logs", expanded=False):
                    display_logs(log_handler)

                # Clear progress
                progress_bar.empty()
                status_text.empty()

                # Display results
                st.success(f"✅ Successfully generated {len(claims_output.claims)} claims!")

                # Search summary
                display_search_summary(claims_output)

                st.markdown("---")

                # Claims
                st.markdown("<div class='phase-header'>📋 Generated Claims</div>", unsafe_allow_html=True)

                if claims_output.claims:
                    for i, claim in enumerate(claims_output.claims):
                        display_claim(claim, i)
                else:
                    st.warning("No claims generated. Try adjusting your query.")

                # Excluded articles
                display_excluded_articles(claims_output)

                # JSON output
                st.markdown("---")
                st.markdown("<div class='phase-header'>📥 Export Results</div>", unsafe_allow_html=True)

                col1, col2 = st.columns(2)

                with col1:
                    # Download JSON
                    json_str = json.dumps(
                        claims_output.model_dump(mode="json"),
                        indent=2,
                        default=str
                    )

                    st.download_button(
                        label="⬇️ Download JSON",
                        data=json_str,
                        file_name=f"claims_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )

                with col2:
                    # Copy to clipboard
                    if st.button("📋 Copy JSON", use_container_width=True):
                        st.code(json_str, language="json")

                # Save to file if requested
                if save_json:
                    output_dir = Path("output")
                    output_dir.mkdir(exist_ok=True)
                    output_file = output_dir / f"claims_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

                    with open(output_file, "w") as f:
                        json.dump(claims_output.model_dump(mode="json"), f, indent=2, default=str)

                    st.info(f"💾 Results saved to: {output_file}")

                # Recommendation
                if claims_output.additional_context.get('recommendation'):
                    st.info(f"💡 {claims_output.additional_context['recommendation']}")

            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.exception(e)

                # Show logs on error
                with st.expander("📜 View Error Logs", expanded=True):
                    display_logs(log_handler)

            finally:
                logger.removeHandler(log_handler)

    elif search_button and not user_query:
        st.warning("⚠️ Please enter a query")


if __name__ == "__main__":
    main()
