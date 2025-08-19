#!/usr/bin/env python3
"""
Fix all incorrect imports in the project
"""
import os
import re
from pathlib import Path

def fix_imports_in_file(filepath):
    """Fix imports in a single file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Fix specific patterns
    replacements = [
        # Fix agent_modules references in non-agent_modules files
        (r'from agent_modules\.([a-z_]+) import', r'from \1 import'),
        # Fix relative imports for models
        (r'from \.\.models import', r'from models import'),
        (r'from \.\.tools import', r'from tools import'),
        (r'from \.\.guardrails import', r'from guardrails import'),
        (r'from \.\.monitoring import', r'from monitoring import'),
        (r'from \.\.nlp import', r'from nlp import'),
        (r'from \.\.integrations import', r'from integrations import'),
        # Fix single dot imports
        (r'from \.([a-z_]+) import', r'from \1 import'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # Special case for agent_modules internal imports
    if 'agent_modules' in str(filepath):
        # Within agent_modules, use relative imports
        content = re.sub(r'from agent_modules\.', r'from .', content)
    
    # Special case for models/__init__.py
    if str(filepath).endswith('models/__init__.py'):
        content = content.replace('from agent_modules.task import', 'from .task import')
        content = content.replace('from agent_modules.event import', 'from .event import')
        content = content.replace('from agent_modules.context import', 'from .context import')
    
    # Special case for tools/__init__.py
    if str(filepath).endswith('tools/__init__.py'):
        content = content.replace('from tools.', 'from .')
    
    # Special case for monitoring/__init__.py
    if str(filepath).endswith('monitoring/__init__.py'):
        content = content.replace('from monitoring.', 'from .')
    
    # Special case for guardrails/__init__.py
    if str(filepath).endswith('guardrails/__init__.py'):
        content = content.replace('from guardrails.', 'from .')
    
    # Special case for nlp/__init__.py
    if str(filepath).endswith('nlp/__init__.py'):
        content = content.replace('from nlp.', 'from .')
    
    # Special case for integrations/__init__.py
    if str(filepath).endswith('integrations/__init__.py'):
        content = content.replace('from integrations.', 'from .')
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
        return True
    return False

def main():
    src_dir = Path(__file__).parent / 'src'
    
    # Find all Python files
    python_files = list(src_dir.rglob('*.py'))
    
    fixed_count = 0
    for filepath in python_files:
        if fix_imports_in_file(filepath):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")

if __name__ == '__main__':
    main()