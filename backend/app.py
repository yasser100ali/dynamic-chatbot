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
        for page in reader.pages[:8]:  # limit for speed
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
    try:
        ai = OpenAI()
        chat = ai.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that extracts presentation metadata and writes a succinct, high-quality system prompt for a chatbot specialized in that presentation."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Given the following extracted text from a slide deck, return strict JSON with keys: "
                        "title (short), description (one sentence), systemPrompt (well-written, concise), "
                        "suggestedActions (array of 4-6 objects with title, label, action). Do not include any additional prose.\n\n"
                        f"TEXT:\n{raw_text[:6000]}"
                    ),
                },
            ],
            temperature=0.2,
        )
        content = chat.choices[0].message.content or "{}"
        import json as _json

        parsed = _json.loads(content)
        title = parsed.get("title")
        description = parsed.get("description")
        system_prompt = parsed.get("systemPrompt")
        if isinstance(parsed.get("suggestedActions"), list):
            suggested = parsed.get("suggestedActions")
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

    if not suggested:
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        headings = []
        for ln in lines:
            if len(ln) < 120 and (ln.istitle() or ln.isupper() or re.match(r"^[-•\d]", ln)):
                headings.append(ln.strip("-• "))
            if len(headings) >= 6:
                break
        for h in headings[:4]:
            suggested.append({
                "title": h[:60],
                "label": f"Ask about: {h[:80]}",
                "action": f"From the presentation, explain the section titled '{h}'. Summarize key points and implications.",
            })

    meta = {
        "title": title[:120] if title else "Presentation",
        "description": description,
        "suggestedActions": suggested,
        "systemPrompt": system_prompt,
        "rawPreview": raw_text[:4000],
    }
    return JSONResponse(content=meta)
