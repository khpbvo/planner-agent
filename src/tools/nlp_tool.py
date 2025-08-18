"""
NLP tool using SpaCy for entity extraction and temporal parsing
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from openai_agents import function_tool
from pydantic import BaseModel
import dateparser
import spacy
from spacy.tokens import Doc

from ..models.context import EntityContext, ExtractedEntity, TemporalReference


class NLPOperation(BaseModel):
    """Input for NLP operations"""
    text: str  # Text to process
    extract_entities: bool = True
    extract_temporal: bool = True
    extract_intent: bool = True
    language: str = "en"


# Global NLP model (will be initialized in create_nlp_tool)
_nlp_model = None

@function_tool
async def process_language(operation_input: NLPOperation) -> str:
        """
        Process natural language text using SpaCy
        
        Args:
            operation_input: NLP operation details
        """
        text = operation_input.text
        
        if not _nlp_model:
            # Fallback to basic processing without SpaCy
            return await basic_nlp_processing(text)
        
        # Process text with SpaCy
        doc = _nlp_model(text)
        
        context = EntityContext(raw_text=text)
        
        # Extract entities
        if operation_input.extract_entities:
            extract_entities(doc, context)
        
        # Extract temporal references
        if operation_input.extract_temporal:
            extract_temporal_references(text, doc, context)
        
        # Extract intent
        if operation_input.extract_intent:
            context.intent = detect_intent(text, doc)
        
        # Format response
        result = {
            "raw_text": context.raw_text,
            "intent": context.intent,
            "entities": [
                {
                    "text": e.text,
                    "label": e.label,
                    "value": str(e.normalized_value) if e.normalized_value else None
                }
                for e in context.entities
            ],
            "temporal_references": [
                {
                    "text": t.original_text,
                    "datetime": t.parsed_datetime.isoformat() if t.parsed_datetime else None,
                    "is_relative": t.is_relative
                }
                for t in context.temporal_refs
            ],
            "people": context.mentioned_people,
            "projects": context.mentioned_projects,
            "locations": context.mentioned_locations
        }
        
        return json.dumps(result, indent=2)
    
def create_nlp_tool(model_name: str = "en_core_web_lg"):
    """Create the NLP tool for natural language processing"""
    global _nlp_model
    
    # Load SpaCy model (would need to be downloaded first)
    try:
        _nlp_model = spacy.load(model_name)
    except:
        # Fallback to small model if large isn't available
        try:
            _nlp_model = spacy.load("en_core_web_sm")
        except:
            _nlp_model = None
    
    return process_language


def extract_entities(doc: Doc, context: EntityContext):
    """Extract named entities from SpaCy doc"""
    
    for ent in doc.ents:
        entity = ExtractedEntity(
            text=ent.text,
            label=ent.label_,
            normalized_value=ent.text
        )
        context.entities.append(entity)
        
        # Categorize by type
        if ent.label_ == "PERSON":
            context.mentioned_people.append(ent.text)
        elif ent.label_ in ["LOC", "GPE", "FAC"]:
            context.mentioned_locations.append(ent.text)
        elif ent.label_ == "ORG":
            # Could be a project or company
            context.mentioned_projects.append(ent.text)


def extract_temporal_references(text: str, doc: Doc, context: EntityContext):
    """Extract and parse temporal references"""
    
    # Common temporal patterns
    temporal_keywords = [
        "today", "tomorrow", "yesterday",
        "next week", "next month", "next year",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "morning", "afternoon", "evening", "night",
        "am", "pm"
    ]
    
    # Extract date entities from SpaCy
    for ent in doc.ents:
        if ent.label_ in ["DATE", "TIME"]:
            parsed_date = dateparser.parse(ent.text, settings={'RELATIVE_BASE': datetime.now()})
            
            temporal_ref = TemporalReference(
                original_text=ent.text,
                parsed_datetime=parsed_date,
                is_relative=any(keyword in ent.text.lower() for keyword in ["today", "tomorrow", "next", "last"])
            )
            context.temporal_refs.append(temporal_ref)
    
    # Also try to parse the full text for complex date expressions
    parsed_full = dateparser.parse(text, settings={'RELATIVE_BASE': datetime.now()})
    if parsed_full and not any(t.parsed_datetime == parsed_full for t in context.temporal_refs):
        context.temporal_refs.append(
            TemporalReference(
                original_text=text,
                parsed_datetime=parsed_full,
                is_relative=True
            )
        )


def detect_intent(text: str, doc: Doc) -> str:
    """Detect user intent from text"""
    
    text_lower = text.lower()
    
    # Intent patterns
    if any(word in text_lower for word in ["schedule", "book", "arrange", "plan", "set up"]):
        return "schedule_event"
    elif any(word in text_lower for word in ["add task", "create task", "todo", "to-do", "remind me"]):
        return "create_task"
    elif any(word in text_lower for word in ["what's on", "show me", "list", "what do i have"]):
        return "query_schedule"
    elif any(word in text_lower for word in ["cancel", "delete", "remove"]):
        return "cancel"
    elif any(word in text_lower for word in ["reschedule", "move", "change time"]):
        return "reschedule"
    elif any(word in text_lower for word in ["complete", "done", "finish", "mark as"]):
        return "complete_task"
    elif any(word in text_lower for word in ["email", "send", "reply"]):
        return "email_action"
    elif any(word in text_lower for word in ["find time", "when can", "available", "free"]):
        return "find_availability"
    else:
        return "general_query"


async def basic_nlp_processing(text: str) -> str:
    """Basic NLP processing without SpaCy"""
    
    # Use dateparser for temporal extraction
    parsed_date = dateparser.parse(text, settings={'RELATIVE_BASE': datetime.now()})
    
    # Basic intent detection
    text_lower = text.lower()
    intent = "general_query"
    
    if "schedule" in text_lower or "meeting" in text_lower:
        intent = "schedule_event"
    elif "task" in text_lower or "todo" in text_lower:
        intent = "create_task"
    elif "show" in text_lower or "list" in text_lower:
        intent = "query_schedule"
    
    result = {
        "raw_text": text,
        "intent": intent,
        "entities": [],
        "temporal_references": [
            {
                "text": text,
                "datetime": parsed_date.isoformat() if parsed_date else None,
                "is_relative": True
            }
        ] if parsed_date else [],
        "people": [],
        "projects": [],
        "locations": []
    }
    
    return json.dumps(result, indent=2)