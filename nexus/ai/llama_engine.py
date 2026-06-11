"""LLaMA AI Engine"""
from llama_cpp import Llama
from nexus.config import settings
from nexus.utils.logger import logger


class LlamaEngine:
    """LLaMA 3.2 AI Engine"""

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load LLaMA model"""
        try:
            self.model = Llama(
                model_path=settings.LLM_MODEL_PATH,
                n_ctx=settings.LLM_CONTEXT_SIZE,
                n_threads=settings.LLM_THREADS,
                verbose=False
            )
            logger.info(f"LLaMA model loaded: {settings.LLM_MODEL_PATH}")
        except Exception as e:
            logger.error(f"Failed to load LLaMA model: {e}")

    def generate_text(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate text using LLaMA"""
        if not self.model:
            return ""

        try:
            output = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=settings.LLM_TEMPERATURE,
                stop=["\n\n\n", "Q:", "A:"]
            )
            return output["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            return ""

    def analyze_lead(self, lead_data: dict) -> dict:
        """Analyze lead and generate insights"""
        prompt = f"""
Analyze this business lead and provide:
1. Quality score (0-100)
2. Key insights
3. Recommendations

Lead Data:
{lead_data}

Analysis:
"""

        response = self.generate_text(prompt, max_tokens=300)

        # Parse response (simplified)
        return {
            'analysis': response,
            'source': 'llama_engine'
        }

    def generate_outreach_message(self, lead_data: dict, context: str = "") -> str:
        """Generate personalized outreach message"""
        prompt = f"""
Write a professional, personalized outreach email to this company.

Lead: {lead_data['company_name']}
Industry: {lead_data.get('industry', 'N/A')}
Context: {context}

Email:
"""

        return self.generate_text(prompt, max_tokens=200)