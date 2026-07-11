# Pi Suite And Nexus Llama 3 Chatbot Spec

Status: Draft  
Owner: Product owner  
Applies to: Pi Suite edge nodes, onsite operations, scraper monitoring, Nexus Llama 3 command assistant, and launch command center

## Pi Suite

The Pi Suite is the edge/field layer for Nexus. It is designed for authorized onsite operations, distributed monitoring, local buffering, and command-center reporting.

### Modules

| Module | Purpose | Launch Requirement |
| --- | --- | --- |
| Field collector | Capture onsite checklists, evidence notes, and approved sensor readings | Device identity and audit logs |
| Offline buffer | Store local findings when internet drops | Encrypted local queue and sync status |
| Source monitor | Watch allowed scraper/source health from distributed locations | Source allowlist and rate limits |
| Device controls | Register, update, disable, and audit Pi nodes | Remote disable and signed updates |

### Guardrails

- Use only on devices and locations where the operator has authorization.
- Do not bypass networks, credentials, or physical access controls.
- Keep local evidence encrypted where practical.
- Sync only necessary records to Nexus.
- Log device registration, check-ins, updates, and disable events.

## Nexus Llama 3 Chatbot

Nexus Llama 3 is the command-center assistant for safe operational workflows.

### Allowed Tasks

- Summarize lead status.
- Explain scraper health and queue status.
- Draft storefront listing copy from sanitized lead fields.
- Guide onsite privacy checklists.
- Explain Pi Suite node status.
- Help with launch readiness, QA, and support workflows.

### Not Allowed

- Covert location tracking.
- Credential theft or bypass instructions.
- Unauthorized scraping or evasion.
- Publishing private lead data without review.
- Claims that AI output is guaranteed accurate.

### Integration Modes

| Mode | Behavior |
| --- | --- |
| Safe fallback | Built-in command-center responses when no Llama endpoint is configured |
| Local Llama | Connect to local Ollama-compatible endpoint such as `http://127.0.0.1:11434/api/chat` |
| Hosted Llama | Connect to a hosted Llama-compatible API through backend environment variables |

### Environment Variables

```text
LLAMA_CHAT_ENDPOINT=http://127.0.0.1:11434/api/chat
LLAMA_CHAT_MODEL=llama3
```

Keep model credentials server-side. Do not expose model API keys in browser code.

