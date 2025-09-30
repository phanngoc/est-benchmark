# 🧠 Fast GraphRAG Document Analyzer

A Streamlit application to test and use [Fast GraphRAG](https://github.com/circlemind-ai/fast-graphrag) for analyzing and querying multiple document files, with a focus on project estimation and task breakdown.

## ✨ Key Features

- 📁 **Multi-format file upload**: TXT, PDF, DOCX, MD
- 🧠 **Intelligent analysis**: Uses Fast GraphRAG to create knowledge graphs
- 🔍 **Natural language queries**: Ask questions in Vietnamese and English
- 📊 **Visualization**: Display relationships between entities
- 📜 **Query history**: Store and manage previously asked questions
- ⚙️ **Flexible configuration**: Customize domain, entity types, example queries

## 🚀 Installation

### 1. Clone repository

```bash
git clone <repository-url>
cd est-benchmark
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment configuration

Create `.env` file from `env.example`:

```bash
cp env.example .env
```

Edit the `.env` file and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
CONCURRENT_TASK_LIMIT=8
```

### 4. Run the application

```bash
streamlit run app.py
```

The application will open at `http://localhost:8501`

## 📖 User Guide

### Step 1: Configuration
1. Open the application in your browser
2. Enter your OpenAI API key in the sidebar
3. Set up domain description (description of the analysis domain)
4. Select entity types (types of entities to identify)
5. Enter example queries (sample questions)
6. Click "Initialize GraphRAG"

### Step 2: Upload documents
1. Navigate to the "Upload Files" tab
2. Select files to analyze (TXT, PDF, DOCX, MD)
3. Click "Process Files" to extract content
4. Click "Add to GraphRAG" to process

### Step 3: Query
1. Navigate to the "Query" tab
2. Enter your question
3. Choose whether to show references or not
4. Click "Search" to get the answer

### Step 4: Visualization
1. Navigate to the "Visualization" tab
2. View statistics and charts about processed data

## 📁 Project Structure

```
est-benchmark/
├── app.py                 # Main Streamlit application
├── config.py             # Configuration
├── requirements.txt      # Dependencies
├── env.example          # Environment file template
├── utils/               # Utility modules
│   ├── __init__.py
│   ├── file_processor.py  # File upload processing
│   ├── graphrag_handler.py # Fast GraphRAG wrapper
│   └── visualization.py   # Graph visualization
├── examples/            # Sample documents
│   └── sample_docs/
│       ├── sample1.txt
│       ├── sample2.txt
│       ├── sample3.txt
│       └── README.md
└── README.md
```

## 🔧 Advanced Configuration

### Default Entity Types
- Category: Development categories
- ParentTask: Main tasks to be implemented
- SubTask: Specific subtasks for each parent task
- Feature: System features
- Component: System components
- API: API endpoints and services
- Database: Database entities and schemas
- Requirement: Functional and non-functional requirements
- Dependency: Task dependencies
- Estimation: Effort and time estimates

### Default Example Queries
- "What development categories does this document contain?"
- "What are the main parent tasks that need to be implemented?"
- "What are the specific subtasks for each parent task?"
- "How are the effort estimates for these tasks calculated?"
- "What are the dependencies between tasks?"
- "How is the priority of tasks determined?"

## 📚 Dependencies

- **streamlit**: Web interface
- **fast-graphrag**: GraphRAG framework
- **openai**: Language model API
- **python-dotenv**: Environment variables
- **pandas**: Data manipulation
- **plotly**: Visualization
- **networkx**: Graph processing
- **PyPDF2**: PDF processing
- **python-docx**: DOCX processing
- **markdown**: Markdown processing

## 🎯 Use Cases

### 1. Project estimation and task breakdown
- Upload project requirements and specifications
- Break down complex projects into categories, parent tasks, and subtasks
- Generate effort estimates and identify dependencies
- Analyze task priorities and resource allocation

### 2. Technical document analysis
- Upload technical specifications, API documentation
- Identify system components, features, and requirements
- Analyze database schemas and API endpoints
- Track dependencies between different system modules

### 3. Software development planning
- Upload user stories, feature requirements
- Categorize development tasks by complexity and priority
- Estimate development effort and timeline
- Identify critical path and potential bottlenecks

### 4. Project management and documentation
- Upload project plans, meeting notes, technical reviews
- Extract actionable tasks and requirements
- Track progress and dependencies
- Generate comprehensive project reports

## 🐛 Troubleshooting

### API Key Error
- Ensure you have entered the correct OpenAI API key
- Check if the API key has sufficient quota

### File Processing Error
- Check if the file format is correct (TXT, PDF, DOCX, MD only)
- Ensure the file is not too large (200MB limit)

### GraphRAG Error
- Ensure GraphRAG has been initialized before use
- Check domain and entity types configuration

## 🤝 Contributing

All contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is distributed under the MIT License. See the `LICENSE` file for more details.

## 🙏 Acknowledgments

- [Fast GraphRAG](https://github.com/circlemind-ai/fast-graphrag) - Main framework
- [Streamlit](https://streamlit.io/) - Web framework
- [OpenAI](https://openai.com/) - Language model API

## 📞 Contact

If you have questions or suggestions, please create an issue on the GitHub repository.
