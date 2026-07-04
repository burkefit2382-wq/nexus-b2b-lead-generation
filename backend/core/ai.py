import os
import asyncio


def _resolve_model(key: str) -> str:
    if key == "qwen":
        return os.environ.get("QWEN_MODEL", "Qwen/Qwen2.5-32B-Instruct")
    if key == "llama":
        return os.environ.get("LLAMA_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
    return os.environ.get("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3.1:novita")

def _active_ai_model(model_key: str = "deepseek") -> str:
    if os.environ.get("AI_PROVIDER", "emergent").lower() == "emergent":
        return f"{os.environ.get('EMERGENT_AI_PROVIDER', 'gemini')}/{os.environ.get('EMERGENT_AI_MODEL', 'gemini-3-flash-preview')}"
    return _resolve_model(model_key)

def _hf_chat_sync(messages, model_key="deepseek", max_tokens=600, temperature=0.4):
    token = os.environ.get("HF_TOKEN", "")
    model = _resolve_model(model_key)
    base = os.environ.get("HF_ROUTER_BASE", "https://router.huggingface.co/v1")
    if not token:
        return {"error": "No HF_TOKEN configured"}
    try:
        from openai import OpenAI
        c = OpenAI(base_url=base, api_key=token)
        r = c.chat.completions.create(model=model, messages=messages,
                                      max_tokens=max_tokens, temperature=temperature)
        return {"content": r.choices[0].message.content, "model": model}
    except Exception as e:
        return {"error": str(e)}

async def _emergent_chat_async(messages, max_tokens=600, temperature=0.4):
    """Text generation via the Emergent Universal Key (emergentintegrations)."""
    key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not key:
        return {"error": "No EMERGENT_LLM_KEY configured"}
    provider = os.environ.get("EMERGENT_AI_PROVIDER", "gemini")
    model = os.environ.get("EMERGENT_AI_MODEL", "gemini-3-flash-preview")
    sys_txt = "\n".join(m["content"] for m in messages if m.get("role") == "system") \
        or "You are a precise intelligence analyst. Follow instructions exactly."
    convo = [m for m in messages if m.get("role") != "system"]
    if not convo:
        return {"error": "No user message"}
    user_text = convo[0]["content"] if len(convo) == 1 else \
        "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in convo)
    try:
        import uuid as _uuid
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=key, session_id=str(_uuid.uuid4()),
                       system_message=sys_txt).with_model(provider, model)
        resp = await chat.send_message(UserMessage(text=user_text))
        text = resp if isinstance(resp, str) else getattr(resp, "content", str(resp))
        return {"content": text, "model": f"{provider}/{model}"}
    except Exception as e:
        return {"error": str(e)}

async def deepseek_chat(messages, model_key="deepseek", **kw):
    """Central AI text helper. Defaults to the Emergent Universal Key; HF router as fallback."""
    if os.environ.get("AI_PROVIDER", "emergent").lower() == "emergent":
        r = await _emergent_chat_async(messages, max_tokens=kw.get("max_tokens", 600),
                                       temperature=kw.get("temperature", 0.4))
        if "error" not in r:
            return r
        if not os.environ.get("HF_TOKEN"):
            return r
    return await asyncio.to_thread(_hf_chat_sync, messages, model_key, **kw)
