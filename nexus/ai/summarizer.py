"""Text summarization and analysis"""
from typing import List, Dict
from nexus.ai.llama_engine import LlamaEngine
from nexus.utils.logger import logger


class Summarizer:
    """Text summarization and analysis"""

    def __init__(self, llm_engine: LlamaEngine):
        self.llm = llm_engine

    def summarize_lead(self, lead_data: Dict) -> str:
        """Summarize lead information"""
        prompt = f"""
Summarize this business lead in 2-3 sentences:

Company: {lead_data['company_name']}
Website: {lead_data.get('website', 'N/A')}
Industry: {lead_data.get('industry', 'N/A')}
Description: {lead_data.get('description', 'N/A')}

Summary:
"""

        return self.llm.generate_text(prompt, max_tokens=150)

    def extract_insights(self, lead_data: Dict, osint_data: Dict) -> List[str]:
        """Extract key insights from combined data"""
        insights = []

        # Basic insights
        if lead_data.get('rating', 0) >= 4.0:
            insights.append("High customer satisfaction rating")

        if lead_data.get('reviews_count', 0) > 100:
            insights.append("Established business with significant customer base")

        # OSINT insights
        if osint_data.get('domain', {}).get('registered'):
            insights.append("Valid domain registration found")

        if osint_data.get('email', {}).get('breached'):
            insights.append("Email address found in data breach")

        if osint_data.get('phone', {}).get('valid'):
            insights.append("Valid phone number format")

        return insights

    def score_lead(self, lead_data: Dict, osint_data: Dict) -> float:
        """Calculate lead quality score (0-100)"""
        score = 0.0

        # Website presence
        if lead_data.get('website'):
            score += 20

        # Contact info
        if lead_data.get('email'):
            score += 15
        if lead_data.get('phone'):
            score += 15

        # Rating
        rating = lead_data.get('rating', 0)
        score += (rating / 5) * 20

        # OSINT validation
        if osint_data.get('domain', {}).get('registered'):
            score += 15

        if not osint_data.get('email', {}).get('breached'):
            score += 15

        return min(score, 100.0)