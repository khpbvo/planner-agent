"""
Advanced NLP Context Management System

Provides sophisticated context tracking, entity resolution, and temporal
understanding for multi-turn conversations in the Planning Assistant.
"""
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import re
import json
import spacy
from spacy.tokens import Doc, Span, Token

from ..models.context import EntityContext, PlanningContext, UserPreferences


class ContextScope(str, Enum):
    """Scope levels for context information"""
    SESSION = "session"      # Entire conversation session
    TURN = "turn"           # Single request-response turn
    TASK = "task"           # Specific task or goal
    ENTITY = "entity"       # Specific entity mention


class ReferenceType(str, Enum):
    """Types of reference resolution"""
    ANAPHORIC = "anaphoric"          # "it", "that", "them"
    CATAPHORIC = "cataphoric"        # Forward references
    TEMPORAL = "temporal"            # "yesterday", "next week"
    SPATIAL = "spatial"              # "here", "there"
    ENTITY_COREFERENCE = "coreference"  # Same entity, different mentions


@dataclass
class ContextualEntity:
    """Enhanced entity with contextual information"""
    text: str
    label: str
    start: int
    end: int
    confidence: float
    
    # Context information
    turn_id: int
    timestamp: datetime
    scope: ContextScope
    
    # Entity resolution
    canonical_id: Optional[str] = None
    aliases: Set[str] = field(default_factory=set)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Temporal information
    resolved_datetime: Optional[datetime] = None
    temporal_relation: Optional[str] = None  # "before", "after", "during"
    
    # Relationships
    related_entities: List[str] = field(default_factory=list)
    dependency_relations: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation"""
    turn_id: int
    timestamp: datetime
    user_input: str
    system_response: Optional[str] = None
    entities: List[ContextualEntity] = field(default_factory=list)
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    resolved_references: Dict[str, str] = field(default_factory=dict)
    context_updates: List[str] = field(default_factory=list)


class AdvancedNLPContextManager:
    """Advanced context management system for NLP processing"""
    
    def __init__(self, spacy_model: str = "en_core_web_lg"):
        # Load SpaCy model
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            # Fallback to smaller model
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                raise RuntimeError("No SpaCy model available. Please install with: python -m spacy download en_core_web_sm")
        
        # Conversation state
        self.turns: List[ConversationTurn] = []
        self.current_turn_id = 0
        self.session_entities: Dict[str, ContextualEntity] = {}
        self.entity_graph: Dict[str, Set[str]] = defaultdict(set)
        
        # Context tracking
        self.active_context: Dict[str, Any] = {}
        self.temporal_context = TemporalContext()
        self.reference_resolver = ReferenceResolver(self)
        self.intent_tracker = IntentTracker()
        
        # Entity coreference resolution
        self.entity_clusters: Dict[str, Set[str]] = defaultdict(set)
        self.canonical_entities: Dict[str, str] = {}
        
        # Recent context window (last N turns for active context)
        self.context_window_size = 5
        self.recent_entities = deque(maxlen=50)
    
    def process_turn(self, 
                    user_input: str, 
                    system_response: Optional[str] = None) -> ConversationTurn:
        """Process a complete conversation turn"""
        
        # Create new turn
        turn = ConversationTurn(
            turn_id=self.current_turn_id,
            timestamp=datetime.now(),
            user_input=user_input,
            system_response=system_response
        )
        
        # Process user input with NLP
        doc = self.nlp(user_input)
        
        # Extract and contextualize entities
        turn.entities = self._extract_contextual_entities(doc, turn)
        
        # Resolve references and coreferences
        self._resolve_references(turn)
        
        # Detect intent
        turn.intent, turn.intent_confidence = self.intent_tracker.detect_intent(user_input, doc)
        
        # Update context
        self._update_context(turn)
        
        # Add to conversation history
        self.turns.append(turn)
        self.current_turn_id += 1
        
        return turn
    
    def _extract_contextual_entities(self, 
                                   doc: Doc, 
                                   turn: ConversationTurn) -> List[ContextualEntity]:
        """Extract entities with contextual enrichment"""
        entities = []
        
        # Standard NER entities
        for ent in doc.ents:
            contextual_ent = ContextualEntity(
                text=ent.text,
                label=ent.label_,
                start=ent.start_char,
                end=ent.end_char,
                confidence=float(ent._.get('confidence', 0.8)),
                turn_id=turn.turn_id,
                timestamp=turn.timestamp,
                scope=ContextScope.TURN
            )
            
            # Temporal entity processing
            if ent.label_ in ['DATE', 'TIME', 'EVENT']:
                contextual_ent.resolved_datetime = self.temporal_context.resolve_temporal_expression(
                    ent.text, turn.timestamp
                )
            
            # Add properties based on entity type
            contextual_ent.properties = self._extract_entity_properties(ent, doc)
            
            entities.append(contextual_ent)
        
        # Custom entity patterns (tasks, priorities, etc.)
        entities.extend(self._extract_custom_entities(doc, turn))
        
        # Update entity tracking
        for entity in entities:
            self._track_entity(entity)
        
        return entities
    
    def _extract_custom_entities(self, doc: Doc, turn: ConversationTurn) -> List[ContextualEntity]:
        """Extract custom entities specific to planning domain"""
        custom_entities = []
        
        # Task-related patterns
        task_patterns = [
            r'(?i)(create|add|make)\s+(?:a\s+)?(?:task|todo|reminder)(?:\s+to)?\s+(.+?)(?:\.|$|with|by)',
            r'(?i)(schedule|plan|book)\s+(.+?)(?:\s+(?:for|at|on|by)|\.|$)',
            r'(?i)(?:need to|have to|must|should)\s+(.+?)(?:\.|$|by|before)'
        ]
        
        text = doc.text
        for pattern in task_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                action = match.group(1).lower()
                task_desc = match.group(2).strip()
                
                if len(task_desc) > 3:  # Filter out very short matches
                    entity = ContextualEntity(
                        text=task_desc,
                        label="TASK",
                        start=match.start(2),
                        end=match.end(2),
                        confidence=0.8,
                        turn_id=turn.turn_id,
                        timestamp=turn.timestamp,
                        scope=ContextScope.TASK,
                        properties={"action": action}
                    )
                    custom_entities.append(entity)
        
        # Priority indicators
        priority_patterns = {
            r'(?i)(urgent|asap|immediately|critical)': 'high',
            r'(?i)(high\s+priority|important|critical)': 'high', 
            r'(?i)(low\s+priority|when\s+you\s+can|eventually)': 'low'
        }
        
        for pattern, priority in priority_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                entity = ContextualEntity(
                    text=match.group(1),
                    label="PRIORITY",
                    start=match.start(1),
                    end=match.end(1),
                    confidence=0.9,
                    turn_id=turn.turn_id,
                    timestamp=turn.timestamp,
                    scope=ContextScope.ENTITY,
                    properties={"priority_level": priority}
                )
                custom_entities.append(entity)
        
        return custom_entities
    
    def _extract_entity_properties(self, ent: Span, doc: Doc) -> Dict[str, Any]:
        """Extract additional properties for entities"""
        properties = {}
        
        # Dependency relations
        properties["dependencies"] = []
        for token in ent:
            for child in token.children:
                properties["dependencies"].append({
                    "relation": child.dep_,
                    "text": child.text,
                    "pos": child.pos_
                })
        
        # Surrounding context
        start_idx = max(0, ent.start - 3)
        end_idx = min(len(doc), ent.end + 3)
        properties["context_window"] = doc[start_idx:end_idx].text
        
        # Entity-specific properties
        if ent.label_ == "PERSON":
            properties["type"] = "person"
            # Look for titles, roles
            for token in doc:
                if token.lower_ in ["mr", "mrs", "dr", "prof"] and abs(token.i - ent.start) <= 2:
                    properties["title"] = token.text
        
        elif ent.label_ in ["DATE", "TIME"]:
            properties["type"] = "temporal"
            properties["original_text"] = ent.text
        
        elif ent.label_ == "ORG":
            properties["type"] = "organization"
        
        return properties
    
    def _track_entity(self, entity: ContextualEntity):
        """Track entity across conversation for coreference resolution"""
        
        # Generate canonical ID if new entity
        if entity.canonical_id is None:
            entity.canonical_id = f"{entity.label}_{len(self.session_entities)}"
        
        # Check for coreference with existing entities
        self._resolve_coreference(entity)
        
        # Add to session entities
        self.session_entities[entity.canonical_id] = entity
        
        # Add to recent entities for context window
        self.recent_entities.append(entity)
        
        # Update entity graph relationships
        self._update_entity_relationships(entity)
    
    def _resolve_coreference(self, entity: ContextualEntity):
        """Resolve coreferences with existing entities"""
        
        # Simple coreference resolution based on text similarity and proximity
        for existing_id, existing_entity in self.session_entities.items():
            
            # Same text, different turns - likely same entity
            if (entity.text.lower() == existing_entity.text.lower() and
                entity.label == existing_entity.label):
                entity.canonical_id = existing_id
                existing_entity.aliases.add(entity.text)
                return
            
            # Similar text for same entity type
            if (entity.label == existing_entity.label and 
                self._text_similarity(entity.text, existing_entity.text) > 0.8):
                entity.canonical_id = existing_id
                existing_entity.aliases.add(entity.text)
                return
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        # Simple Jaccard similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _update_entity_relationships(self, entity: ContextualEntity):
        """Update relationships between entities"""
        
        # Find entities in the same turn for relationship detection
        current_turn_entities = [e for e in self.recent_entities 
                               if e.turn_id == entity.turn_id]
        
        for other_entity in current_turn_entities:
            if other_entity.canonical_id != entity.canonical_id:
                # Add bidirectional relationship
                self.entity_graph[entity.canonical_id].add(other_entity.canonical_id)
                self.entity_graph[other_entity.canonical_id].add(entity.canonical_id)
                
                # Update related entities lists
                if other_entity.canonical_id not in entity.related_entities:
                    entity.related_entities.append(other_entity.canonical_id)
    
    def _resolve_references(self, turn: ConversationTurn):
        """Resolve pronomial and temporal references"""
        turn.resolved_references = self.reference_resolver.resolve_references(
            turn.user_input, turn.entities, self.get_recent_context()
        )
    
    def _update_context(self, turn: ConversationTurn):
        """Update conversation context based on new turn"""
        
        # Update active entities (entities mentioned recently)
        active_entities = {}
        for entity in turn.entities:
            active_entities[entity.canonical_id] = entity
        
        # Maintain temporal context
        self.temporal_context.update_from_turn(turn)
        
        # Update intent context
        self.intent_tracker.update_context(turn.intent, turn.intent_confidence)
        
        # Update active context with key information
        self.active_context.update({
            "last_intent": turn.intent,
            "active_entities": list(active_entities.keys()),
            "current_turn": turn.turn_id,
            "timestamp": turn.timestamp.isoformat()
        })
    
    def get_context_for_entity(self, entity_text: str) -> Dict[str, Any]:
        """Get comprehensive context for a specific entity"""
        
        # Find all mentions of this entity
        mentions = []
        canonical_id = None
        
        for turn in self.turns:
            for entity in turn.entities:
                if (entity.text.lower() == entity_text.lower() or 
                    entity_text.lower() in [alias.lower() for alias in entity.aliases]):
                    mentions.append(entity)
                    if canonical_id is None:
                        canonical_id = entity.canonical_id
        
        if not mentions:
            return {"error": "Entity not found in conversation"}
        
        # Compile context
        context = {
            "canonical_id": canonical_id,
            "mentions": len(mentions),
            "first_mentioned": mentions[0].timestamp.isoformat(),
            "last_mentioned": mentions[-1].timestamp.isoformat(),
            "aliases": list(set().union(*[m.aliases for m in mentions])),
            "properties": {},
            "relationships": list(self.entity_graph.get(canonical_id, [])),
            "mention_contexts": []
        }
        
        # Merge properties from all mentions
        for mention in mentions:
            context["properties"].update(mention.properties)
            context["mention_contexts"].append({
                "turn_id": mention.turn_id,
                "text": mention.text,
                "context": mention.properties.get("context_window", ""),
                "confidence": mention.confidence
            })
        
        return context
    
    def get_recent_context(self, window_size: Optional[int] = None) -> Dict[str, Any]:
        """Get recent conversation context"""
        
        window_size = window_size or self.context_window_size
        recent_turns = self.turns[-window_size:] if window_size > 0 else self.turns
        
        context = {
            "turns": len(recent_turns),
            "entities": [],
            "intents": [],
            "temporal_references": [],
            "active_tasks": []
        }
        
        for turn in recent_turns:
            context["intents"].append({
                "intent": turn.intent,
                "confidence": turn.intent_confidence,
                "turn_id": turn.turn_id
            })
            
            for entity in turn.entities:
                entity_summary = {
                    "text": entity.text,
                    "label": entity.label,
                    "canonical_id": entity.canonical_id,
                    "turn_id": entity.turn_id
                }
                
                if entity.label == "TASK":
                    context["active_tasks"].append(entity_summary)
                elif entity.resolved_datetime:
                    context["temporal_references"].append({
                        **entity_summary,
                        "resolved_datetime": entity.resolved_datetime.isoformat()
                    })
                else:
                    context["entities"].append(entity_summary)
        
        return context
    
    def export_conversation_context(self) -> Dict[str, Any]:
        """Export complete conversation context for analysis"""
        
        return {
            "session_info": {
                "total_turns": len(self.turns),
                "total_entities": len(self.session_entities),
                "entity_clusters": len(self.entity_clusters),
                "start_time": self.turns[0].timestamp.isoformat() if self.turns else None,
                "end_time": self.turns[-1].timestamp.isoformat() if self.turns else None
            },
            "turns": [
                {
                    "turn_id": turn.turn_id,
                    "timestamp": turn.timestamp.isoformat(),
                    "user_input": turn.user_input,
                    "intent": turn.intent,
                    "intent_confidence": turn.intent_confidence,
                    "entities": [
                        {
                            "text": e.text,
                            "label": e.label,
                            "canonical_id": e.canonical_id,
                            "confidence": e.confidence,
                            "properties": e.properties
                        } for e in turn.entities
                    ],
                    "resolved_references": turn.resolved_references
                } for turn in self.turns
            ],
            "entity_graph": {
                entity_id: list(related_ids) 
                for entity_id, related_ids in self.entity_graph.items()
            },
            "temporal_context": self.temporal_context.export_state(),
            "active_context": self.active_context
        }


class TemporalContext:
    """Manages temporal understanding and context"""
    
    def __init__(self):
        self.reference_time = datetime.now()
        self.temporal_anchors: Dict[str, datetime] = {}
        self.recurring_patterns: List[Dict[str, Any]] = []
    
    def resolve_temporal_expression(self, text: str, reference_time: datetime) -> Optional[datetime]:
        """Resolve temporal expressions to specific datetime"""
        
        text_lower = text.lower().strip()
        
        # Relative expressions
        if text_lower in ['today', 'now']:
            return reference_time.replace(hour=0, minute=0, second=0, microsecond=0)
        elif text_lower in ['tomorrow']:
            return reference_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif text_lower in ['yesterday']:
            return reference_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        elif text_lower == 'next week':
            days_ahead = 7 - reference_time.weekday()
            return reference_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
        elif text_lower == 'last week':
            days_back = reference_time.weekday() + 7
            return reference_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_back)
        
        # Time expressions
        time_patterns = {
            r'(\d{1,2}):(\d{2})\s*(am|pm)': self._parse_time_12h,
            r'(\d{1,2}):(\d{2})': self._parse_time_24h,
            r'(\d{1,2})\s*(am|pm)': self._parse_hour_12h
        }
        
        for pattern, parser in time_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                return parser(match, reference_time)
        
        return None
    
    def _parse_time_12h(self, match, reference_time: datetime) -> datetime:
        """Parse 12-hour time format"""
        hour = int(match.group(1))
        minute = int(match.group(2))
        period = match.group(3)
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        return reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    def _parse_time_24h(self, match, reference_time: datetime) -> datetime:
        """Parse 24-hour time format"""
        hour = int(match.group(1))
        minute = int(match.group(2))
        
        return reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    def _parse_hour_12h(self, match, reference_time: datetime) -> datetime:
        """Parse hour-only 12h format"""
        hour = int(match.group(1))
        period = match.group(2)
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        return reference_time.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    def update_from_turn(self, turn: ConversationTurn):
        """Update temporal context from a conversation turn"""
        self.reference_time = turn.timestamp
        
        # Track temporal anchors mentioned in conversation
        for entity in turn.entities:
            if entity.resolved_datetime:
                self.temporal_anchors[entity.text] = entity.resolved_datetime
    
    def export_state(self) -> Dict[str, Any]:
        """Export temporal context state"""
        return {
            "reference_time": self.reference_time.isoformat(),
            "temporal_anchors": {
                k: v.isoformat() for k, v in self.temporal_anchors.items()
            },
            "recurring_patterns": self.recurring_patterns
        }


class ReferenceResolver:
    """Resolves pronouns and other references"""
    
    def __init__(self, context_manager):
        self.context_manager = context_manager
    
    def resolve_references(self, 
                         text: str, 
                         entities: List[ContextualEntity],
                         recent_context: Dict[str, Any]) -> Dict[str, str]:
        """Resolve references in text"""
        
        resolved = {}
        
        # Simple pronoun resolution
        pronouns = {
            'it': self._resolve_pronoun_it,
            'that': self._resolve_pronoun_that,
            'this': self._resolve_pronoun_this,
            'them': self._resolve_pronoun_them,
            'they': self._resolve_pronoun_they
        }
        
        for pronoun, resolver in pronouns.items():
            if pronoun in text.lower():
                resolution = resolver(recent_context)
                if resolution:
                    resolved[pronoun] = resolution
        
        return resolved
    
    def _resolve_pronoun_it(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'it' pronoun"""
        # Look for most recent singular entity
        for entity_info in reversed(context.get("entities", [])):
            if entity_info["label"] in ["TASK", "EVENT", "ORG"]:
                return entity_info["text"]
        return None
    
    def _resolve_pronoun_that(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'that' reference"""
        # Look for most recent task or event
        for task in reversed(context.get("active_tasks", [])):
            return task["text"]
        
        for entity_info in reversed(context.get("entities", [])):
            if entity_info["label"] in ["EVENT", "TASK"]:
                return entity_info["text"]
        return None
    
    def _resolve_pronoun_this(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'this' reference"""
        # Similar to 'that' but prefer more recent mentions
        recent_entities = context.get("entities", [])[-3:]  # Last 3 entities
        for entity_info in reversed(recent_entities):
            return entity_info["text"]
        return None
    
    def _resolve_pronoun_them(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'them' pronoun"""
        # Look for plural entities or multiple recent entities
        persons = [e for e in context.get("entities", []) if e["label"] == "PERSON"]
        if len(persons) > 1:
            return ", ".join([p["text"] for p in persons[-2:]])
        return None
    
    def _resolve_pronoun_they(self, context: Dict[str, Any]) -> Optional[str]:
        """Resolve 'they' pronoun"""
        return self._resolve_pronoun_them(context)


class IntentTracker:
    """Tracks user intents across conversation"""
    
    def __init__(self):
        self.intent_history: List[Tuple[str, float, datetime]] = []
        self.intent_patterns = {
            'schedule': [
                r'(?i)(schedule|book|plan|set up)\s+(?:a\s+)?(?:meeting|appointment|call)',
                r'(?i)(?:when|what time).*(?:free|available)',
                r'(?i)(?:add|create).*(?:calendar|schedule)'
            ],
            'task_create': [
                r'(?i)(?:add|create|make)\s+(?:a\s+)?(?:task|todo|reminder)',
                r'(?i)(?:need to|have to|must|should)\s+(?:remember to)?',
                r'(?i)(?:remind me to|don\'t forget to)'
            ],
            'task_query': [
                r'(?i)(?:what|which|show me).*(?:tasks|todos|things to do)',
                r'(?i)(?:my|current|pending)\s+(?:tasks|todos|work)',
                r'(?i)(?:what do I have|what am I supposed to do)'
            ],
            'calendar_query': [
                r'(?i)(?:what\'s|what is).*(?:on my calendar|scheduled)',
                r'(?i)(?:show me|check)\s+(?:my\s+)?(?:calendar|schedule|agenda)',
                r'(?i)(?:do I have|am I).*(?:meeting|appointment|busy)'
            ],
            'email_process': [
                r'(?i)(?:check|read|process|go through)\s+(?:my\s+)?(?:email|inbox|mail)',
                r'(?i)(?:any|new|unread)\s+(?:emails|messages)',
                r'(?i)(?:extract|find).*(?:action items|tasks).*(?:email|mail)'
            ],
            'planning': [
                r'(?i)(?:plan|organize|optimize|balance)\s+(?:my\s+)?(?:day|week|schedule|time)',
                r'(?i)(?:help me|can you).*(?:organize|plan|schedule)',
                r'(?i)(?:best time|when should I|optimal)'
            ]
        }
    
    def detect_intent(self, text: str, doc: Optional[Doc] = None) -> Tuple[Optional[str], float]:
        """Detect user intent from text"""
        
        text_lower = text.lower()
        best_intent = None
        best_score = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    # Score based on match length and position
                    score = len(match.group(0)) / len(text) * 0.7
                    if match.start() < len(text) * 0.3:  # Early in sentence
                        score += 0.2
                    
                    if score > best_score:
                        best_score = score
                        best_intent = intent
        
        # Additional scoring based on entities and POS patterns
        if doc and best_intent:
            best_score = min(1.0, best_score + self._score_with_linguistics(doc, best_intent))
        
        return best_intent, best_score
    
    def _score_with_linguistics(self, doc: Doc, intent: str) -> float:
        """Add linguistic features to intent scoring"""
        bonus = 0.0
        
        # Look for imperative mood (commands)
        if intent in ['task_create', 'schedule'] and doc[0].tag_ in ['VB', 'VBP']:
            bonus += 0.15
        
        # Look for question words for query intents
        if intent.endswith('_query') and any(token.tag_ in ['WP', 'WRB', 'WDT'] for token in doc):
            bonus += 0.1
        
        return bonus
    
    def update_context(self, intent: Optional[str], confidence: float):
        """Update intent tracking context"""
        if intent:
            self.intent_history.append((intent, confidence, datetime.now()))
            
            # Keep only recent history
            if len(self.intent_history) > 20:
                self.intent_history = self.intent_history[-15:]
    
    def get_intent_context(self) -> Dict[str, Any]:
        """Get current intent context"""
        if not self.intent_history:
            return {"current_intent": None}
        
        recent_intents = self.intent_history[-5:]  # Last 5 intents
        intent_counts = defaultdict(int)
        
        for intent, confidence, timestamp in recent_intents:
            if confidence > 0.5:  # Only count confident intents
                intent_counts[intent] += 1
        
        return {
            "current_intent": self.intent_history[-1][0] if self.intent_history else None,
            "current_confidence": self.intent_history[-1][1] if self.intent_history else 0.0,
            "recent_pattern": dict(intent_counts),
            "intent_history_length": len(self.intent_history)
        }