# Suggested Development Commands

## Installation and Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp env.example .env
# Edit .env file with your OpenAI API key
```

## Running the Application
```bash
# Main Streamlit application
streamlit run app.py

# Alternative run script (with dependency checks)
python run.py

# Run on specific port
streamlit run app.py --server.port 8501
```

## Development Commands
```bash
# Check Python files
python -m py_compile app.py
python -m py_compile config.py
python -m py_compile estimation_workflow.py

# List Python files
find . -name "*.py" -type f

# Check imports
python -c "import streamlit, fast_graphrag, openai, langchain, langgraph"
```

## File Operations
```bash
# Check project structure
ls -la
tree -I '__pycache__|*.pyc|.git'

# View logs (if any)
tail -f streamlit.log

# Clean cache
rm -rf __pycache__ utils/__pycache__
```

## Git Operations
```bash
git status
git add .
git commit -m "message"
git push origin feat/workflow
```

## Environment Management
```bash
# Check environment variables
cat .env

# Validate configuration
python -c "from config import Config; Config.validate_config()"
```