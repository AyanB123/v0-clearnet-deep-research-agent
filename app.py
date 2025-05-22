import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import json
import time
from crawler import ClearnetCrawler
from knowledge_base import KnowledgeBase
from agent import ResearchAgent
from utils import setup_logger, get_current_timestamp
import os

# Setup logger
logger = setup_logger()

# Page config
st.set_page_config(
    page_title="Clearnet Research Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "crawled_data" not in st.session_state:
    st.session_state.crawled_data = {}
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = KnowledgeBase()
if "agent" not in st.session_state:
    st.session_state.agent = ResearchAgent()
if "report" not in st.session_state:
    st.session_state.report = ""
if "graph" not in st.session_state:
    st.session_state.graph = None

# Title and description
st.title("🔍 Clearnet Research Assistant")
st.markdown("""
This tool helps you research topics by crawling websites, analyzing content, and generating reports.
All crawling is done ethically, respecting robots.txt and website terms of service.
""")

# Sidebar for configuration
with st.sidebar:
    st.header("Research Configuration")
    
    query = st.text_area("Research Query", 
                         placeholder="E.g., Analyze tech blogs for AI trends",
                         help="What would you like to research?")
    
    seed_url = st.text_input("Seed URL", 
                             placeholder="https://example.com",
                             help="Starting point for the crawler")
    
    st.subheader("Advanced Settings")
    
    model = st.selectbox(
        "AI Model",
        ["groq/llama3-8b-8192", "groq/llama3-70b-8192", "groq/mixtral-8x7b-32768"],
        help="Select the AI model for analysis"
    )
    
    crawl_depth = st.slider(
        "Crawl Depth",
        min_value=1,
        max_value=10,
        value=3,
        help="How deep to crawl from the seed URL"
    )
    
    mode = st.selectbox(
        "Research Mode",
        ["Exploratory", "Deep Dive", "Stealth"],
        help="Exploratory: Broad crawling, Deep Dive: Focused extraction, Stealth: Minimized footprint"
    )
    
    link_limit = st.slider(
        "Links Per Page",
        min_value=1,
        max_value=20,
        value=5,
        help="Maximum number of links to follow per page"
    )
    
    respect_robots = st.checkbox(
        "Respect robots.txt",
        value=True,
        help="Follow robots.txt directives"
    )
    
    st.button(
        "Clear Data",
        on_click=lambda: [
            st.session_state.pop("crawled_data", None),
            st.session_state.pop("report", None),
            st.session_state.pop("graph", None),
            st.session_state.__setitem__("crawled_data", {}),
            st.session_state.__setitem__("report", ""),
            st.session_state.__setitem__("graph", None),
            st.session_state.knowledge_base.clear()
        ]
    )

# Main content area with tabs
tab1, tab2, tab3 = st.tabs(["Research", "Visualization", "Raw Data"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("Start Research", disabled=not (query and seed_url)):
            with st.spinner("Researching..."):
                # Initialize crawler with configuration
                crawler = ClearnetCrawler(
                    respect_robots=respect_robots,
                    crawl_depth=crawl_depth,
                    link_limit=link_limit,
                    mode=mode.lower()
                )
                
                # Progress bar
                progress = st.progress(0)
                status_text = st.empty()
                
                # Step 1: Crawling
                status_text.text("Step 1/3: Crawling websites...")
                crawled_data = crawler.crawl(seed_url)
                st.session_state.crawled_data = crawled_data
                progress.progress(33)
                
                # Step 2: Indexing
                status_text.text("Step 2/3: Indexing content...")
                for url, data in crawled_data.items():
                    st.session_state.knowledge_base.add_document(
                        text=data["content"],
                        metadata={"url": url, "timestamp": get_current_timestamp()}
                    )
                progress.progress(66)
                
                # Step 3: Analysis
                status_text.text("Step 3/3: Analyzing and generating report...")
                st.session_state.report = st.session_state.agent.analyze(
                    query=query,
                    crawled_data=crawled_data,
                    knowledge_base=st.session_state.knowledge_base,
                    model=model
                )
                
                # Create graph
                G = nx.DiGraph()
                for url, data in crawled_data.items():
                    G.add_node(url)
                    for link in data.get("links", []):
                        G.add_edge(url, link)
                st.session_state.graph = G
                
                progress.progress(100)
                status_text.text("Research complete!")
                time.sleep(1)
                status_text.empty()
                progress.empty()
        
        # Display report
        if st.session_state.report:
            st.markdown("## Research Report")
            st.markdown(st.session_state.report)
    
    with col2:
        st.markdown("### Research Status")
        if st.session_state.crawled_data:
            st.success(f"Crawled {len(st.session_state.crawled_data)} pages")
            st.info(f"Indexed {st.session_state.knowledge_base.count()} documents")
            
            # Show crawled URLs
            with st.expander("Crawled URLs"):
                for url in st.session_state.crawled_data.keys():
                    st.write(url)

with tab2:
    if st.session_state.graph:
        st.markdown("## Link Network Visualization")
        st.markdown("This graph shows the connections between crawled pages.")
        
        # Create visualization
        fig, ax = plt.subplots(figsize=(10, 8))
        pos = nx.spring_layout(st.session_state.graph)
        nx.draw(
            st.session_state.graph, 
            pos, 
            with_labels=False, 
            node_color='skyblue', 
            node_size=100, 
            edge_color='gray', 
            arrows=True,
            ax=ax
        )
        
        # Add labels to larger nodes
        node_sizes = {node: st.session_state.graph.degree(node) * 10 for node in st.session_state.graph.nodes()}
        large_nodes = [node for node, size in node_sizes.items() if size > 50]
        labels = {node: node.split('/')[-1] for node in large_nodes}
        nx.draw_networkx_labels(st.session_state.graph, pos, labels=labels, font_size=8, ax=ax)
        
        st.pyplot(fig)
        
        # Network statistics
        st.markdown("### Network Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nodes", len(st.session_state.graph.nodes()))
        with col2:
            st.metric("Edges", len(st.session_state.graph.edges()))
        with col3:
            if len(st.session_state.graph.nodes()) > 0:
                density = nx.density(st.session_state.graph)
                st.metric("Density", f"{density:.4f}")
    else:
        st.info("Run a research query to generate a link network visualization.")

with tab3:
    if st.session_state.crawled_data:
        st.markdown("## Raw Crawled Data")
        st.json(st.session_state.crawled_data)
    else:
        st.info("Run a research query to see raw data.")

# Footer
st.markdown("---")
st.markdown("Clearnet Research Assistant | Ethically crawling the web for research purposes")
