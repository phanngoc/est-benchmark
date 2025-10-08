# Project Overview

## Purpose
Fast GraphRAG Document Analyzer - A Streamlit application for testing and using Fast GraphRAG for document analysis and querying. The project focuses on breaking down technical documents into categories, parent tasks, and sub-tasks with effort estimation.

## Main Features
- Multi-format file upload (TXT, PDF, DOCX, MD)
- Smart analysis using Fast GraphRAG to create knowledge graphs
- Natural language querying in Vietnamese
- Task breakdown and estimation workflow
- Visualization of entity relationships
- Query history management
- Excel export functionality

## Project Architecture
- **app.py**: Main Streamlit application with multi-tab interface
- **config.py**: Configuration management with environment variables
- **utils/**: Core functionality modules
  - **graphrag_handler.py**: Wrapper for Fast GraphRAG operations
  - **file_processor.py**: File upload and content extraction
  - **visualization.py**: Graph visualization and statistics
- **estimation_workflow.py**: LangGraph-based workflow for task estimation
- **examples/**: Sample documents and tasks for testing
- **graphrag_workspace/**: Working directory for GraphRAG operations