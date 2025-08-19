"""
NLP tool using SpaCy for entity extraction and temporal parsing
Enhanced with advanced context management capabilities
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from agents import function_tool
from pydantic import BaseModel
import dateparser
import spacy
from spacy.tokens import Doc

from models.context import EntityContext, ExtractedEntity, TemporalReference
from nlp.context_manager import AdvancedNLPContextManager


class NLPOperation(BaseModel):
    """Input for NLP operations"""
    text: str  # Text to process
    extract_entities: bool = True
    extract_temporal: bool = True
    extract_intent: bool = True
    extract_context: bool = True
    resolve_references: bool = True
    language: str = "en"
    session_id: Optional[str] = None


class ContextQuery(BaseModel):
    """Query for context information"""
    query_type: str  # "entity", "recent", "export", "analytics"
    entity_text: Optional[str] = None
    window_size: Optional[int] = None
    session_id: Optional[str] = None


# Global NLP components (will be initialized in create_nlp_tool)
_nlp_model = None
_context_managers: Dict[str, AdvancedNLPContextManager] = {}  # session_id -> context_manager

@function_tool(strict_json_schema=False)
async def process_language(operation_input: NLPOperation) -> str:
        """
        Process natural language text using advanced NLP and context management
        
        Args:
            operation_input: NLP operation details
        """
        text = operation_input.text
        session_id = operation_input.session_id or "default"
        
        if not _nlp_model:
            # Fallback to basic processing without SpaCy
            return await basic_nlp_processing(text)
        
        # Get or create context manager for this session
        if session_id not in _context_managers:
            _context_managers[session_id] = AdvancedNLPContextManager()
        
        context_manager = _context_managers[session_id]
        
        # Process the turn with advanced context management
        if operation_input.extract_context:
            turn = context_manager.process_turn(text)
            
            # Prepare comprehensive response
            response_data = {
                "status": "success",
                "turn_id": turn.turn_id,
                "processing_timestamp": turn.timestamp.isoformat(),
                
                # Basic NLP results
                "entities": [
                    {
                        "text": e.text,
                        "label": e.label,
                        "start": e.start,
                        "end": e.end,
                        "confidence": e.confidence,
                        "canonical_id": e.canonical_id,
                        "resolved_datetime": e.resolved_datetime.isoformat() if e.resolved_datetime else None,
                        "properties": e.properties
                    } for e in turn.entities
                ],
                
                "intent": {
                    "intent": turn.intent,
                    "confidence": turn.intent_confidence
                } if operation_input.extract_intent else None,
                
                # Advanced context features
                "resolved_references": turn.resolved_references if operation_input.resolve_references else {},
                
                "context_updates": turn.context_updates,
                
                "recent_context": context_manager.get_recent_context(3) if operation_input.extract_context else None
            }
            
            return json.dumps(response_data, indent=2)
        
        else:
            # Fallback to basic processing
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
        print(f"✓ Loaded SpaCy model: {model_name}")
    except:
        # Fallback to small model if large isn't available
        try:
            _nlp_model = spacy.load("en_core_web_sm")
            print("✓ Loaded fallback SpaCy model: en_core_web_sm")
        except:
            _nlp_model = None
            print("⚠️ No SpaCy models available, using basic NLP processing")
    
    return process_language


def create_nlp_tools(model_name: str = "en_core_web_lg"):
    """Create both NLP processing tools with advanced context management"""
    create_nlp_tool(model_name)  # Initialize the global model
    return [process_language, query_context]


def get_context_manager(session_id: str = "default") -> Optional[AdvancedNLPContextManager]:
    """Get the context manager for a specific session"""
    return _context_managers.get(session_id)


def reset_context(session_id: str = "default"):
    """Reset context for a specific session"""
    if session_id in _context_managers:
        del _context_managers[session_id]
        
        
def get_active_sessions() -> List[str]:
    """Get list of active NLP context sessions"""
    return list(_context_managers.keys())


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
    """Extract and parse temporal references with enhanced patterns"""
    
    import re
    
    # Enhanced temporal patterns
    temporal_patterns = [
        # Specific times
        r'\b(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b',
        # Relative days
        r'\b(today|tomorrow|yesterday)\b',
        # This/next/last patterns
        r'\b(this|next|last)\s+(week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        # In X time patterns
        r'\bin\s+(\d+)\s+(minutes?|hours?|days?|weeks?|months?)\b',
        # Weekdays
        r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        # Dates with various formats
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
        r'\b(\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december))\b',
    ]
    
    # Extract temporal entities from SpaCy
    for ent in doc.ents:
        if ent.label_ in ["DATE", "TIME", "EVENT"]:
            parsed_date = dateparser.parse(
                ent.text, 
                settings={
                    'RELATIVE_BASE': datetime.now(),
                    'PREFER_DATES_FROM': 'future',
                    'TIMEZONE': 'UTC'
                }
            )
            
            if parsed_date:
                temporal_ref = TemporalReference(
                    original_text=ent.text,
                    parsed_datetime=parsed_date,
                    is_relative=any(keyword in ent.text.lower() 
                                  for keyword in ["today", "tomorrow", "next", "last", "this"])
                )
                context.temporal_refs.append(temporal_ref)
    
    # Use regex patterns to find additional temporal references
    for pattern in temporal_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            temporal_text = match.group(0)
            
            # Skip if already captured by SpaCy
            if any(temporal_text in ref.original_text for ref in context.temporal_refs):
                continue
                
            parsed_date = dateparser.parse(
                temporal_text,
                settings={
                    'RELATIVE_BASE': datetime.now(),
                    'PREFER_DATES_FROM': 'future',
                    'TIMEZONE': 'UTC'
                }
            )
            
            if parsed_date:
                temporal_ref = TemporalReference(
                    original_text=temporal_text,
                    parsed_datetime=parsed_date,
                    is_relative=True
                )
                context.temporal_refs.append(temporal_ref)
    
    # Try to parse the full text for complex expressions
    full_parsed = dateparser.parse(
        text, 
        settings={
            'RELATIVE_BASE': datetime.now(),
            'PREFER_DATES_FROM': 'future',
            'TIMEZONE': 'UTC'
        }
    )
    
    if full_parsed and not any(abs((t.parsed_datetime - full_parsed).total_seconds()) < 60 
                              for t in context.temporal_refs if t.parsed_datetime):
        context.temporal_refs.append(
            TemporalReference(
                original_text=text,
                parsed_datetime=full_parsed,
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


@function_tool(strict_json_schema=False)
async def query_context(query_input: ContextQuery) -> str:
    """
    Query contextual information from conversation history
    
    Args:
        query_input: Context query details
    """
    session_id = query_input.session_id or "default"
    
    if session_id not in _context_managers:
        return json.dumps({
            "status": "error",
            "message": f"No context available for session {session_id}",
            "suggestion": "Process some text first to build context"
        }, indent=2)
    
    context_manager = _context_managers[session_id]
    
    try:
        if query_input.query_type == "entity":
            if not query_input.entity_text:
                return json.dumps({
                    "status": "error", 
                    "message": "entity_text required for entity query"
                }, indent=2)
            
            entity_context = context_manager.get_context_for_entity(query_input.entity_text)
            return json.dumps({
                "status": "success",
                "query_type": "entity",
                "entity_text": query_input.entity_text,
                "context": entity_context
            }, indent=2)
        
        elif query_input.query_type == "recent":
            window_size = query_input.window_size or 5
            recent_context = context_manager.get_recent_context(window_size)
            return json.dumps({
                "status": "success",
                "query_type": "recent",
                "window_size": window_size,
                "context": recent_context
            }, indent=2)
        
        elif query_input.query_type == "export":
            full_context = context_manager.export_conversation_context()
            return json.dumps({
                "status": "success",
                "query_type": "export",
                "conversation_context": full_context
            }, indent=2)
        
        elif query_input.query_type == "analytics":
            analytics = {
                "session_id": session_id,
                "total_turns": len(context_manager.turns),
                "total_entities": len(context_manager.session_entities),
                "entity_relationships": len(context_manager.entity_graph),
                "intent_history_length": len(context_manager.intent_tracker.intent_history),
                "recent_intents": [
                    {"intent": intent, "confidence": conf, "timestamp": ts.isoformat()} 
                    for intent, conf, ts in context_manager.intent_tracker.intent_history[-5:]
                ]
            }
            return json.dumps({
                "status": "success",
                "query_type": "analytics", 
                "analytics": analytics
            }, indent=2)
        
        else:
            return json.dumps({
                "status": "error",
                "message": f"Unknown query type: {query_input.query_type}",
                "supported_types": ["entity", "recent", "export", "analytics"]
            }, indent=2)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Context query failed: {str(e)}",
            "query_type": query_input.query_type
        }, indent=2)