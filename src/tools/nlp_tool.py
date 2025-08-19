from __future__ import annotations
from typing import List, Any
from datetime import datetime
from pydantic import BaseModel
import dateparser


class NLPOperation(BaseModel):
    """Input for NLP operations"""
    text: str


class NLPResponse(BaseModel):
    """Structured NLP processing result"""
    raw_text: str
    intent: str
    entities: List[Any]
    temporal_references: List[Any]
    people: List[str] = []
    projects: List[str] = []
    locations: List[str] = []


async def process_language(operation_input: NLPOperation) -> NLPResponse:
    """Process natural language text."""
    return await basic_nlp_processing(operation_input.text)


async def basic_nlp_processing(text: str) -> NLPResponse:
    """Basic NLP processing without SpaCy."""
    parsed_date = dateparser.parse(text, settings={'RELATIVE_BASE': datetime.now()})
    text_lower = text.lower()
    intent = "general_query"
    if "schedule" in text_lower or "meeting" in text_lower:
        intent = "schedule_event"
    elif "task" in text_lower or "todo" in text_lower:
        intent = "create_task"
    elif "show" in text_lower or "list" in text_lower:
        intent = "query_schedule"

    temporal_refs = []
    if parsed_date:
        temporal_refs.append(
            {
                "text": text,
                "datetime": parsed_date.isoformat(),
                "is_relative": True,
            }
        )

    return NLPResponse(
        raw_text=text,
        intent=intent,
        entities=[],
        temporal_references=temporal_refs,
    )
