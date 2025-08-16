import os
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, JSONResponse
from base64 import b64decode
import re
from pydantic import BaseModel
from io import BytesIO
from pypdf import PdfReader
from openai import OpenAI
from .utils.prompt import (
    ClientMessage,
    convert_to_openai_messages,
    HEALTHCARE_SYSTEM_PROMPT,
    build_dynamic_system_prompt,
)
from .utils.utils import stream_text


load_dotenv(".env")

app = FastAPI()


class Request(BaseModel):
    messages: List[ClientMessage]
    system: Optional[dict] = None


@app.post("/api/chat")
async def handle_chat_data(request: Request, protocol: str = Query('data')):
    print("Received request in handle_chat_data")
    user_messages = request.messages

    # Build a dynamic prompt if presentation data is available from the client
    dynamic_prompt = None
    if request.system and isinstance(request.system, dict):
        title = str(request.system.get("title") or "Presentation")
        raw_preview = str(request.system.get("rawPreview") or "")
        system_prompt_hint = request.system.get("systemPrompt")
        if isinstance(system_prompt_hint, str) and system_prompt_hint.strip():
            dynamic_prompt = system_prompt_hint
        elif raw_preview:
            dynamic_prompt = build_dynamic_system_prompt(title, raw_preview)

    # Prepend dynamic system prompt if present; else default prompt
    system_message = ClientMessage(
        role="system",
        content=dynamic_prompt or HEALTHCARE_SYSTEM_PROMPT,
    )
    messages = [system_message, *user_messages]

    openai_messages = convert_to_openai_messages(messages)
    print("Messages sent to OpenAI:", openai_messages)

    response = StreamingResponse(stream_text(openai_messages, protocol))
    response.headers['x-vercel-ai-data-stream'] = 'v1'
    return response


class PresentationMetaRequest(BaseModel):
    pdf_data_url: str
    filename: Optional[str] = None


@app.post("/api/presentation_meta")
async def presentation_meta(req: PresentationMetaRequest):
    # pdf_data_url is expected to be a data URL (data:application/pdf;base64,....)
    match = re.match(r"^data:application\/pdf;?base64,(.*)$", req.pdf_data_url)
    if not match:
        return JSONResponse(status_code=400, content={"error": "Invalid PDF data URL"})

    try:
        pdf_bytes = b64decode(match.group(1), validate=False)
        reader = PdfReader(BytesIO(pdf_bytes))
        text_chunks = []
        for page in reader.pages[:20]:  # read more pages to improve coverage
            try:
                text_chunks.append(page.extract_text() or "")
            except Exception:
                continue
        raw_text = "\n".join(text_chunks).strip()
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Failed to parse PDF: {e}"})

    # Try to have the AI synthesize a system prompt and metadata from the text
    system_prompt = None
    title = None
    description = None
    suggested = []
    topics = []
    
    def _extract_json(text: str) -> dict:
        import json as _json
        # Some models may wrap JSON in prose or code fences; try to extract the first JSON object
        text_strip = text.strip()
        if text_strip.startswith("{") and text_strip.endswith("}"):
            return _json.loads(text_strip)
        # Find the first opening brace and last closing brace
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return _json.loads(text[start:end+1])
            except Exception:
                pass
        # Fallback
        return {}
    try:
        ai = OpenAI()
        chat = ai.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return STRICT JSON only, no prose. Read slide text and produce: "
                        "title (short), description (single sentence), systemPrompt (concise, high quality), "
                        "topics (8-12 concise bullet points summarizing core ideas), "
                        "suggestedActions (5-8 objects with title, label, action that lead to useful follow-ups). "
                        "Avoid trivial/boilerplate like authorship, agenda, Q&A, or thank-you slides."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"TEXT:\n{raw_text[:6000]}\n\n"
                        "Return JSON with keys exactly: {\"title\", \"description\", \"systemPrompt\", \"topics\", \"suggestedActions\"}."
                    ),
                },
            ],
            temperature=0.2,
        )
        content = chat.choices[0].message.content or "{}"
        parsed = _extract_json(content)
        title = parsed.get("title")
        description = parsed.get("description")
        system_prompt = parsed.get("systemPrompt")
        if isinstance(parsed.get("suggestedActions"), list):
            suggested = parsed.get("suggestedActions")
        if isinstance(parsed.get("topics"), list):
            topics = parsed.get("topics")
    except Exception:
        pass

    # Fallback heuristics if the AI parsing failed
    if not title:
        if reader.metadata and reader.metadata.title:
            title = str(reader.metadata.title)
        if not title:
            first_lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()][:5]
            title = first_lines[0] if first_lines else (req.filename or "Presentation")

    if not description:
        description = "This chatbot adapts to your uploaded presentation, summarizing sections and answering questions grounded in the file."

    def _is_trivial(text: str) -> bool:
        if not text:
            return True
        t = text.strip().lower()
        bad_prefixes = [
            "by ",
            "agenda",
            "table of contents",
            "contents",
            "q&a",
            "qa",
            "thank you",
            "thanks",
            "overview",
        ]
        return any(t.startswith(p) for p in bad_prefixes)

    if suggested:
        cleaned = []
        for a in suggested:
            title_a = (a.get("title") or "").strip()
            label_a = (a.get("label") or "").strip()
            action_a = (a.get("action") or "").strip()
            if not _is_trivial(title_a) and len(title_a) >= 3:
                cleaned.append({"title": title_a, "label": label_a, "action": action_a})
        suggested = cleaned[:8]

    if not suggested:
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        headings = []
        for ln in lines:
            if len(ln) < 120 and (ln.istitle() or ln.isupper() or re.match(r"^[-•\d]", ln)):
                cand = ln.strip("-• ")
                if not _is_trivial(cand):
                    headings.append(cand)
            if len(headings) >= 10:
                break
        for h in headings[:6]:
            suggested.append({
                "title": h[:60],
                "label": f"Ask about: {h[:80]}",
                "action": f"From the presentation, explain the section titled '{h}'. Summarize key points and implications.",
            })

    # Ensure topics are present; if empty, try a last-resort AI pass
    if not topics:
        try:
            ai2 = OpenAI()
            chat2 = ai2.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": "Return a JSON array of 8-12 short bullet topics for the deck. No prose."},
                    {"role": "user", "content": f"TEXT:\n{raw_text[:6000]}"},
                ],
                temperature=0.2,
            )
            import json as _json
            raw2 = chat2.choices[0].message.content or "[]"
            s = raw2.strip()
            if not s.startswith("["):
                start = s.find("[")
                end = s.rfind("]")
                if start != -1 and end != -1 and end > start:
                    s = s[start:end+1]
            arr = _json.loads(s)
            if isinstance(arr, list):
                def _clean_topic(t: str) -> str:
                    t2 = t.strip()
                    lower = t2.lower()
                    blacklist_prefixes = [
                        "by ",
                        "contents",
                        "table of contents",
                        "agenda",
                        "q&a",
                        "qa",
                        "thank",
                        "thanks",
                        "overview",
                    ]
                    for b in blacklist_prefixes:
                        if lower.startswith(b):
                            return ""
                    return t2
                topics = [t for t in map(_clean_topic, arr) if isinstance(t, str) and t]
        except Exception:
            pass

    meta = {
        "title": title[:120] if title else "Presentation",
        "description": description,
        "suggestedActions": suggested,
        "systemPrompt": system_prompt,
        "topics": topics,
        "rawPreview": raw_text[:4000],
    }
    return JSONResponse(content=meta)
