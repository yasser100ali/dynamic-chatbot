import json
from enum import Enum
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from pydantic import BaseModel
import base64
from typing import List, Optional, Any
from .attachment import ClientAttachment

class ToolInvocationState(str, Enum):
    CALL = 'call'
    PARTIAL_CALL = 'partial-call'
    RESULT = 'result'

class ToolInvocation(BaseModel):
    state: ToolInvocationState
    toolCallId: str
    toolName: str
    args: Any
    result: Any


class ClientMessage(BaseModel):
    role: str
    content: str
    experimental_attachments: Optional[List[ClientAttachment]] = None
    toolInvocations: Optional[List[ToolInvocation]] = None

def convert_to_openai_messages(messages: List[ClientMessage]) -> List[ChatCompletionMessageParam]:
    openai_messages = []

    for message in messages:
        parts = []
        tool_calls = []

        parts.append({
            'type': 'text',
            'text': message.content
        })

        if (message.experimental_attachments):
            for attachment in message.experimental_attachments:
                if (attachment.contentType.startswith('image')):
                    parts.append({
                        'type': 'image_url',
                        'image_url': {
                            'url': attachment.url
                        }
                    })

                elif (attachment.contentType.startswith('text')):
                    parts.append({
                        'type': 'text',
                        'text': attachment.url
                    })

        if(message.toolInvocations):
            for toolInvocation in message.toolInvocations:
                tool_calls.append({
                    "id": toolInvocation.toolCallId,
                    "type": "function",
                    "function": {
                        "name": toolInvocation.toolName,
                        "arguments": json.dumps(toolInvocation.args)
                    }
                })

        tool_calls_dict = {"tool_calls": tool_calls} if tool_calls else {"tool_calls": None}

        openai_messages.append({
            "role": message.role,
            "content": parts,
            **tool_calls_dict,
        })

        if(message.toolInvocations):
            for toolInvocation in message.toolInvocations:
                tool_message = {
                    "role": "tool",
                    "tool_call_id": toolInvocation.toolCallId,
                    "content": json.dumps(toolInvocation.result),
                }

                openai_messages.append(tool_message)

    return openai_messages

# Generic base system prompt for any presentation/topic.
HEALTHCARE_SYSTEM_PROMPT = """
You are an educational chatbot that answers concisely, factually, and in a well-structured format. Always:
- Be clear and organized with short sections, bullet points, and small tables where helpful.
- State assumptions and uncertainty; avoid fabricating citations or facts.
- Focus on the user's question first; ask a brief clarifying question if the prompt is ambiguous.
- Keep responses compact (typically under 200 words) unless asked for depth.
"""


def build_dynamic_system_prompt(presentation_title: str, raw_preview: str) -> str:
    """Create a short, focused system prompt grounded in the uploaded presentation.

    The preview should be a compact extract from the PDF text. We keep the
    same safety and style tenets, but make the assistant condition its answers
    on the uploaded content where possible.
    """
    base = HEALTHCARE_SYSTEM_PROMPT
    preface = f"""
Adapt to the uploaded presentation: "{presentation_title}".
Ground answers primarily in this deck. When outside scope, say so briefly and proceed with general knowledge if appropriate.
Use this excerpt to anchor context (do not repeat verbatim unless asked):

Be efficient in your speech, and use tables when necessary. 

--- Presentation excerpt  ---
{raw_preview}
--- End excerpt ---

Generate a specialized persona and topic framing consistent with the deck. Prefer concise summaries, key takeaways, and actionable suggestions.
If the question is outside the presentation, note that explicitly.

"""

    print(f"\n\nHere is the raw preview: \n\n{raw_preview}\n\n")
    return preface + "\n\n" + base
