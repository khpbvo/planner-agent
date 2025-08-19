"""
Advanced NLP package for the Planning Assistant

Provides sophisticated natural language processing capabilities including:
- Contextual entity extraction and resolution  
- Temporal understanding and parsing
- Intent detection and tracking
- Reference resolution (pronouns, coreferences)
- Multi-turn conversation context management
- Entity relationship mapping
"""

from context_manager import (
    AdvancedNLPContextManager,
    ContextualEntity,
    ConversationTurn,
    TemporalContext,
    ReferenceResolver,
    IntentTracker,
    ContextScope,
    ReferenceType
)

__all__ = [
    # Core context management
    'AdvancedNLPContextManager',
    'ContextualEntity', 
    'ConversationTurn',
    
    # Specialized components
    'TemporalContext',
    'ReferenceResolver', 
    'IntentTracker',
    
    # Enums
    'ContextScope',
    'ReferenceType'
]


def create_context_manager(spacy_model: str = "en_core_web_lg") -> AdvancedNLPContextManager:
    """
    Create a new NLP context manager instance
    
    Args:
        spacy_model: SpaCy model to use for NLP processing
        
    Returns:
        AdvancedNLPContextManager: Configured context manager
    """
    return AdvancedNLPContextManager(spacy_model)


def get_supported_intents() -> dict:
    """Get list of supported intent types and their descriptions"""
    return {
        'schedule': 'Scheduling meetings, appointments, or events',
        'task_create': 'Creating tasks, todos, or reminders',  
        'task_query': 'Querying existing tasks or todos',
        'calendar_query': 'Checking calendar, schedule, or availability',
        'email_process': 'Processing, reading, or managing emails',
        'planning': 'Planning, organizing, or optimizing schedules'
    }


def get_supported_entity_types() -> dict:
    """Get list of supported entity types and their descriptions"""
    return {
        # Standard NER types
        'PERSON': 'People names and references',
        'ORG': 'Organizations, companies, institutions',
        'DATE': 'Dates and date ranges',
        'TIME': 'Times and time ranges',
        'EVENT': 'Events, meetings, appointments',
        'GPE': 'Geopolitical entities (cities, countries)',
        'MONEY': 'Monetary values',
        'CARDINAL': 'Numbers and quantities',
        
        # Planning-specific types
        'TASK': 'Tasks, todos, action items',
        'PRIORITY': 'Priority levels and indicators',
        'PROJECT': 'Projects and work categories',
        'DURATION': 'Time durations and periods'
    }


def get_context_features() -> list:
    """Get list of available context management features"""
    return [
        'entity_coreference_resolution',
        'temporal_expression_parsing', 
        'intent_tracking_across_turns',
        'pronoun_and_reference_resolution',
        'entity_relationship_mapping',
        'conversation_history_analysis',
        'context_window_management',
        'multi_session_support'
    ]