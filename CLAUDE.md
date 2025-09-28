# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Fast GraphRAG Document Analyzer** - a Streamlit application that uses Fast GraphRAG for intelligent document analysis and task estimation. The application focuses on breaking down technical documents into categories, parent tasks, and sub-tasks with effort estimation for software development projects.

## Core Development Commands

### Setup and Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp env.example .env
# Edit .env file with your OpenAI API key
```

### Running the Application
```bash
# Primary method - Main Streamlit app
streamlit run app.py

# Alternative method - Enhanced run script with dependency checks
python run.py

# Custom port
streamlit run app.py --server.port 8501
```

### Code Validation
```bash
# Validate Python syntax (no formal testing framework)
python -m py_compile app.py
python -m py_compile config.py
python -m py_compile estimation_workflow.py
python -m py_compile utils/*.py

# Verify imports work
python -c "from config import Config; Config.validate_config()"
python -c "from utils.graphrag_handler import GraphRAGHandler; print('Handler loaded')"
```

## Architecture Overview

### Core Components
- **app.py**: Main Streamlit application with multi-tab interface (Configuration, Upload, Query, Visualization)
- **config.py**: Centralized configuration with environment variable management
- **estimation_workflow.py**: LangGraph-based workflow for task breakdown and estimation
- **utils/**: Core functionality modules
  - `graphrag_handler.py`: Fast GraphRAG wrapper with session management
  - `file_processor.py`: Multi-format file processing (TXT, PDF, DOCX, MD)
  - `visualization.py`: Graph visualization and statistics

### Data Flow Architecture
1. **Document Upload** → File processing → Content extraction
2. **GraphRAG Processing** → Entity extraction → Knowledge graph creation
3. **Task Analysis** → LangGraph workflow → Task breakdown → Effort estimation
4. **Visualization** → Network graphs → Statistics → Excel export

### Key Design Patterns
- **Handler Pattern**: External library wrappers (GraphRAGHandler)
- **Configuration Pattern**: Centralized config with validation
- **Session State Pattern**: Streamlit session persistence
- **Workflow Pattern**: LangGraph state machines for task estimation

## Technology Stack

### Core Framework
- **Streamlit**: Web interface with multi-tab navigation
- **Fast GraphRAG**: Knowledge graph creation and document analysis
- **LangGraph**: Workflow orchestration with state graphs
- **LangChain**: LLM integration and prompt management

### AI/ML Stack
- **OpenAI API**: GPT-4o-mini for text processing (configurable model)
- **LangChain OpenAI**: OpenAI integration layer

### Data Processing
- **pandas**: Data manipulation and Excel export
- **PyPDF2**: PDF processing
- **python-docx**: Word document processing
- **networkx**: Graph processing and analysis

## Configuration Requirements

### Environment Variables
Create `.env` file with:
```env
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
CONCURRENT_TASK_LIMIT=8
```

### Default Configuration
- **Domain Focus**: Technical document analysis with task breakdown
- **Entity Types**: Category, ParentTask, SubTask, Feature, Component, API, Database, Requirement, Dependency, Estimation
- **Working Directory**: `./graphrag_workspace`
- **File Size Limit**: 200MB
- **Supported Formats**: TXT, PDF, DOCX, MD

## Code Style and Conventions

### Python Style
- **Classes**: PascalCase (`GraphRAGHandler`, `FileProcessor`)
- **Functions/Methods**: snake_case (`insert_documents`, `get_graph_info`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_FILE_SIZE`, `DEFAULT_DOMAIN`)
- **Files**: snake_case (`file_processor.py`)

### Documentation
- **Docstrings**: For classes and main functions
- **Type Hints**: Extensive use with typing module
- **Comments**: Mixed Vietnamese (UI/business) and English (technical)

### Import Organization
```python
# Standard library
import os, json
# Third-party
import streamlit as st
# Local modules
from config import Config
```

## Development Workflow

### Quality Assurance (No Formal Testing)
Since this project lacks formal testing frameworks (pytest, unittest), use manual validation:

1. **Syntax Check**: All Python files must compile without errors
2. **Import Check**: All dependencies must import successfully
3. **Configuration Check**: `Config.validate_config()` must pass
4. **Runtime Check**: Streamlit application must start without errors
5. **Feature Check**: Manual testing of core workflows

### Task Completion Checklist
- [ ] Python files compile: `python -m py_compile <file>`
- [ ] Configuration validates: `Config.validate_config()`
- [ ] Application starts: `streamlit run app.py`
- [ ] Core functionality works: Upload → Process → Query → Visualize
- [ ] No runtime errors in Streamlit interface

## Key Working Directories

- **graphrag_workspace/**: Fast GraphRAG working directory (auto-created)
- **examples/**: Sample documents and task templates
- **utils/**: Core utility modules
- **.env**: Environment configuration (create from env.example)

## Estimation Workflow Features

The project includes a sophisticated **LangGraph-based estimation workflow** that:
- Breaks down requirements into task hierarchies
- Estimates effort for middle developers (3 years experience)
- Generates Mermaid diagrams for visualization
- Exports results to Excel with detailed breakdowns
- Handles dependencies and complexity assessment

## Important Notes

- **Language**: Mixed Vietnamese (UI) and English (code) - maintain this pattern
- **API Key**: OpenAI API key required for all functionality
- **GraphRAG Initialization**: Must initialize GraphRAG before document processing
- **Session Persistence**: Uses Streamlit session state for cross-tab persistence
- **File Limits**: 200MB max file size, multiple format support

## Common Development Tasks

### Adding New File Processors
1. Extend `FileProcessor` class in `utils/file_processor.py`
2. Add new file extension to `Config.ALLOWED_EXTENSIONS`
3. Update file upload validation in main app

### Extending Entity Types
1. Modify `Config.DEFAULT_ENTITY_TYPES`
2. Update example queries in `Config.DEFAULT_EXAMPLE_QUERIES`
3. Test with sample documents

### Customizing Estimation Workflow
1. Modify workflow nodes in `estimation_workflow.py`
2. Adjust prompts for different developer experience levels
3. Update Excel export format as needed