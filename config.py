import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the Fast GraphRAG Streamlit app"""
    
    # OpenAI API Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    CONCURRENT_TASK_LIMIT = int(os.getenv("CONCURRENT_TASK_LIMIT", "8"))
    
    # App Configuration
    APP_TITLE = "Fast GraphRAG Document Analyzer"
    APP_DESCRIPTION = "Analyze and query documents with Fast GraphRAG"
    
    # File Upload Configuration
    MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
    ALLOWED_EXTENSIONS = ['.txt', '.pdf', '.docx', '.md']
    
    # GraphRAG Configuration
    DEFAULT_DOMAIN = "Focus on analyzing technical documents and breaking tasks into categories, parent tasks, sub tasks with estimation."
    DEFAULT_ENTITY_TYPES = ["Category", "ParentTask", "SubTask", "Feature", "Component", "API", "Database", "Requirement", "Dependency", "Estimation"]
    DEFAULT_EXAMPLE_QUERIES = [
        "What development categories does this document contain?",
        "What are the main parent tasks that need to be implemented?",
        "What are the specific subtasks for each parent task?",
        "How are the effort estimates for these tasks calculated?",
        "What are the dependencies between tasks?",
        "How is the priority of tasks determined?"
    ]

    # Working Directory
    WORKING_DIR = "./graphrag_workspace"
    
    # Visualization Configuration
    GRAPH_LAYOUT = "spring"  # spring, circular, random, shell, etc.
    MAX_NODES_DISPLAY = 100
    

    @classmethod
    def validate_config(cls):
        """Validate configuration settings"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required. Please set it in your environment or .env file")
        return True
