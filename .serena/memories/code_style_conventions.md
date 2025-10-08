# Code Style and Conventions

## Python Style
- **PEP 8**: Standard Python style guide followed
- **Class names**: PascalCase (e.g., `GraphRAGHandler`, `FileProcessor`)
- **Function/method names**: snake_case (e.g., `insert_documents`, `get_graph_info`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_FILE_SIZE`, `DEFAULT_DOMAIN`)
- **Variable names**: snake_case
- **File names**: snake_case (e.g., `file_processor.py`, `graphrag_handler.py`)

## Documentation
- **Docstrings**: Used for classes and main functions
- **Type hints**: Used extensively with typing module
- **Comments**: Vietnamese and English mixed, focusing on business logic explanation
- **Configuration**: Centralized in `config.py` with class-based organization

## Project Structure Patterns
- **Utils pattern**: Separate utility classes in `utils/` directory
- **Handler pattern**: Wrapper classes for external libraries (e.g., `GraphRAGHandler`)
- **Config pattern**: Centralized configuration with validation
- **Session state**: Streamlit session state for persistence

## Import Organization
```python
# Standard library imports first
import os
import json
from datetime import datetime

# Third-party imports
import streamlit as st
import pandas as pd

# Local imports last
from config import Config
from utils.graphrag_handler import GraphRAGHandler
```

## Error Handling
- Configuration validation in `Config.validate_config()`
- Try-catch blocks for external API calls
- User-friendly error messages in Vietnamese for UI
- Defensive programming for file operations

## Naming Conventions
- **Vietnamese**: UI text, user messages, comments explaining business logic
- **English**: Code, function names, technical documentation
- **Mixed approach**: Vietnamese for domain-specific terms, English for technical terms