"""AI API routes"""
from fastapi import APIRouter, HTTPException
from typing import Dict
from nexus.ai.llama_engine import LlamaEngine
from nexus.ai.summarizer import Summarizer
from nexus.ai.embeddings import Embeddings
from nexus.utils.logger import logger

router = APIRouter()

# Initialize AI modules
try:
    llama_engine = LlamaEngine()
    summarizer = Summarizer(llama_engine)
    embeddings = Embeddings()
except Exception as e:
    logger.error(f"Failed to initialize AI modules: {e}")
    llama_engine = None
    summarizer = None
    embeddings = None


@router.post("/generate")
async def generate_text(prompt: str, max_tokens: int = 512):
    """Generate text using LLaMA"""
    if not llama_engine:
        raise HTTPException(status_code=503, detail="LLaMA engine not available")

    try:
        result = llama_engine.generate_text(prompt, max_tokens=max_tokens)
        return {"text": result, "source": "llama_engine"}
    except Exception as e:
        logger.error(f"Text generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_lead(lead_data: Dict):
    """Analyze lead using AI"""
    if not llama_engine:
        raise HTTPException(status_code=503, detail="LLaMA engine not available")

    try:
        result = llama_engine.analyze_lead(lead_data)
        return result
    except Exception as e:
        logger.error(f"Lead analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize")
async def summarize_lead(lead_data: Dict):
    """Summarize lead information"""
    if not summarizer:
        raise HTTPException(status_code=503, detail="Summarizer not available")

    try:
        summary = summarizer.summarize_lead(lead_data)
        return {"summary": summary, "source": "summarizer"}
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/score")
async def score_lead(lead_data: Dict, osint_data: Dict):
    """Calculate lead quality score"""
    if not summarizer:
        raise HTTPException(status_code=503, detail="Summarizer not available")

    try:
        score = summarizer.score_lead(lead_data, osint_data)
        return {"quality_score": score, "source": "summarizer"}
    except Exception as e:
        logger.error(f"Scoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outreach")
async def generate_outreach(lead_data: Dict, context: str = ""):
    """Generate personalized outreach message"""
    if not llama_engine:
        raise HTTPException(status_code=503, detail="LLaMA engine not available")

    try:
        message = llama_engine.generate_outreach_message(lead_data, context)
        return {"message": message, "source": "llama_engine"}
    except Exception as e:
        logger.error(f"Outreach generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embed")
async def create_embedding(text: str):
    """Create text embedding"""
    if not embeddings:
        raise HTTPException(status_code=503, detail="Embeddings model not available")

    try:
        embedding = embeddings.encode(text)
        return {"embedding": embedding, "source": "embeddings"}
    except Exception as e:
        logger.error(f"Embedding creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similarity")
async def calculate_similarity(text1: str, text2: str):
    """Calculate semantic similarity between two texts"""
    if not embeddings:
        raise HTTPException(status_code=503, detail="Embeddings model not available")

    try:
        similarity = embeddings.similarity(text1, text2)
        return {"similarity": similarity, "source": "embeddings"}
    except Exception as e:
        logger.error(f"Similarity calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))