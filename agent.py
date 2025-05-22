import logging
import json
from ai import generateText
from groq import groq
from utils import setup_logger

# Setup logger
logger = setup_logger()

class ResearchAgent:
    def __init__(self):
        """Initialize the research agent"""
        logger.info("Initializing Research Agent")
    
    def analyze(self, query, crawled_data, knowledge_base, model="groq/llama3-8b-8192"):
        """
        Analyze crawled data and generate a report.
        
        Args:
            query (str): Research query
            crawled_data (dict): Crawled website data
            knowledge_base (KnowledgeBase): Knowledge base instance
            model (str): AI model to use
            
        Returns:
            str: Markdown report
        """
        logger.info(f"Starting analysis with model {model}")
        
        # Get relevant documents from knowledge base
        relevant_docs = knowledge_base.query(query, n_results=5)
        
        # Prepare context from crawled data and knowledge base
        context = self._prepare_context(query, crawled_data, relevant_docs)
        
        # Generate report using AI
        report = self._generate_report(query, context, model)
        
        return report
    
    def _prepare_context(self, query, crawled_data, relevant_docs):
        """Prepare context for the AI model"""
        # Extract summary of crawled data
        crawled_summary = {
            "num_pages": len(crawled_data),
            "pages": []
        }
        
        # Add page summaries (limit to avoid token limits)
        for url, data in list(crawled_data.items())[:10]:  # Limit to 10 pages
            page_summary = {
                "url": url,
                "title": data.get("metadata", {}).get("title", "No title"),
                "content_preview": data.get("content", "")[:500] + "..." if len(data.get("content", "")) > 500 else data.get("content", ""),
                "num_links": len(data.get("links", []))
            }
            crawled_summary["pages"].append(page_summary)
        
        # Format relevant documents
        kb_docs = []
        for doc in relevant_docs:
            kb_docs.append({
                "text": doc["text"][:1000] + "..." if len(doc["text"]) > 1000 else doc["text"],
                "source": doc["metadata"].get("url", "Unknown source")
            })
        
        # Combine into context
        context = {
            "query": query,
            "crawled_data": crawled_summary,
            "relevant_documents": kb_docs
        }
        
        return context
    
    def _generate_report(self, query, context, model):
        """Generate report using AI"""
        try:
            # Prepare system prompt
            system_prompt = """You are a research assistant that analyzes web content and generates comprehensive reports.
Your task is to analyze the provided context and create a detailed, well-structured report that addresses the research query.

Your report should:
1. Begin with an executive summary
2. Include key findings organized by themes or categories
3. Cite sources using [Source: URL] format
4. Include a conclusion with insights and recommendations
5. Be formatted in Markdown with proper headings, lists, and emphasis

Base your analysis only on the provided context. If the context is insufficient, acknowledge the limitations.
"""

            # Prepare user prompt
            user_prompt = f"""Research Query: {query}

Context:
{json.dumps(context, indent=2)}

Please generate a comprehensive research report based on this information.
"""

            # Generate text using AI SDK
            response = generateText({
                "model": groq(model),
                "system": system_prompt,
                "prompt": user_prompt,
                "temperature": 0.7,
                "max_tokens": 4000
            })
            
            logger.info(f"Generated report with {len(response.text)} characters")
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"""# Error Generating Report

Unfortunately, an error occurred while generating the report: {str(e)}

## Raw Data Summary
- Query: {query}
- Pages crawled: {context['crawled_data']['num_pages']}
- Relevant documents: {len(context['relevant_documents'])}
"""
