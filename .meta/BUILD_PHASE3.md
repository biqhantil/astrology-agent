# Build Phase 3 - Communication Layer: SSE + Conversations + LLM

## Context

The backend has:
- Auth (JWT anonymous + magic-link) - working
- Users, BirthProfiles CRUD - working
- Natal chart computation (Swiss Ephemeris) - working
- Transits, Synastry, Life Phases engines - working
- All 12 DB tables (including conversations, messages) - migrated
- Frontend SPA (React + Vite + ZodiacWheel) - built

The frontend is a chat-based SPA that:
- Auto-logs in anonymously via JWT
- Connects to GET /v1/stream with conversation_id query via SSE
- Sends messages via POST conversations endpoint
- Renders chart components when SSE events arrive

## Build Order (in sequence)

### 1. Conversation Schemas
Create these files following existing pattern in backend/app/schemas/:

File: backend/app/schemas/conversation.py
- Pydantic v2 models for creating, listing, updating conversations
- Fields: id UUID, user_id UUID, chart_context_id UUID optional, synastry_context_id UUID optional, title str optional, status str, created_at, updated_at

File: backend/app/schemas/message.py  
- Pydantic v2 models for messages
- Fields: id int, conversation_id UUID, role str (system/user/assistant/tool), content str, tool_call_id optional, tool_name optional, payload optional dict

### 2. Conversation Router
File: backend/app/routers/conversations.py
- POST /v1/conversations - create new conversation (user_id from JWT)
- GET /v1/conversations - list user's conversations
- GET /v1/conversations/{id} - get conversation with messages
- PATCH /v1/conversations/{id} - update title/status
- DELETE /v1/conversations/{id} - archive (set status=archived)
- Use require_user dependency from app.core.auth
- Use get_conn dependency for DB access

### 3. Message Router
File: backend/app/routers/messages.py
- POST /v1/conversations/{id}/messages - send a new message
  - Creates user message in DB
  - Calls LLM to generate response
  - Stores assistant message in DB
  - Returns both messages
- GET /v1/conversations/{id}/messages - list messages (paginated)

### 4. SSE Stream Endpoint
File: backend/app/routers/stream.py
- GET /v1/stream with conversation_id query parameter - SSE connection
- Maintains per-user connection state (dict of asyncio.Queue)
- Supports event types: chat.delta (streaming text tokens), chart.data (full chart payload), transit.data, synastry.data, component.render, session.status, error
- When LLM calls a tool, result is pushed to this queue for the conversation

### 5. LLM Integration - Client
File: backend/app/llm/client.py
- Async HTTP client for OpenCode Go API
- Reads OPENCODE_API_KEY from environment
- Sends messages array + system prompt
- Handles streaming chunked response
- Returns text + tool_calls
- Model: deepseek-v4-flash via opencode-go provider

### 6. LLM Integration - Prompts
File: backend/app/llm/prompts.py
- System prompt template with chart context injection
- Instructions for when to use chart tools vs direct text response
- Tone: wise, insightful astrologer

### 7. LLM Integration - Tools
File: backend/app/llm/tools.py
- JSON Schema definitions for available tools:
  - render_natal_chart(user_id)
  - render_transit_timeline(chart_id, start_date, end_date)
  - render_synastry(chart_a_id, chart_b_id)
  - render_life_phases(user_id)
- Tool execution functions that call the existing engine modules

### 8. Wire Everything Together
Edit backend/app/main.py:
- Import and include: conversations.router (prefix=/v1), messages.router (prefix=/v1), stream.router (prefix=/v1)
- Remove the commented-out placeholder imports

## Implementation Pattern Reference

Each router follows this pattern:
```python
from fastapi import APIRouter, Depends
from app.core.auth import require_user
from app.core.deps import get_conn

router = APIRouter()

@router.get("/endpoint")
async def handler(
    auth = Depends(require_user),
    conn = Depends(get_conn),
):
    # use auth["sub"] for user_id
    # use conn for DB queries
    return {"result": "ok"}
```

## Verification
1. Start backend: cd /opt/astrology-agent/backend && source venv/bin/activate && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/astro-api.log 2>&1 &
2. Test health: curl http://localhost:8000/v1/health
3. Create conversation: curl -X POST http://localhost:8000/v1/conversations -H "Content-Type: application/json" -d '{}'
4. Each step should pass before moving to next
