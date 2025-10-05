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

    # Logging Configuration
    LOG_DIR = os.getenv("LOG_DIR", "./logs")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB per log file
    LOG_BACKUP_COUNT = 30  # Keep 30 backup files
    LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
    
    # App Configuration
    APP_TITLE = "Fast GraphRAG Document Analyzer"
    APP_DESCRIPTION = "Phân tích và truy vấn tài liệu với Fast GraphRAG"
    
    # File Upload Configuration
    MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
    ALLOWED_EXTENSIONS = ['.txt', '.pdf', '.docx', '.md']
    
    # GraphRAG Configuration
    DEFAULT_DOMAIN = "Tập trung vào phân tích tài liệu kỹ thuật và break task thành category, parent task, sub task với estimation."
    DEFAULT_ENTITY_TYPES = ["Category", "ParentTask", "SubTask", "Feature", "Component", "API", "Database", "Requirement", "Dependency", "Estimation"]
    DEFAULT_EXAMPLE_QUERIES = [
        "Tài liệu này có những category phát triển nào?",
        "Các parent tasks chính cần thực hiện là gì?",
        "Sub tasks cụ thể cho từng parent task là gì?",
        "Ước tính effort cho các tasks này như thế nào?",
        "Dependencies giữa các tasks là gì?",
        "Priority của các tasks được xác định ra sao?"
    ]

    # Working Directory
    WORKING_DIR = "./graphrag_workspace"
    UPLOADS_DIR = "./uploads"
    RESULT_EST_DIR = "./result_est"  # Dedicated folder for estimation Excel files

    # File Metadata Configuration
    METADATA_FILE = ".metadata.json"
    HASH_ALGORITHM = "sha256"
    
    # Visualization Configuration
    GRAPH_LAYOUT = "spring"  # spring, circular, random, shell, etc.
    MAX_NODES_DISPLAY = 100
    

    # Estimation History Configuration
    ESTIMATION_HISTORY_DB_PATH = "./estimation_history_db"
    ESTIMATION_HISTORY_COLLECTION = "estimation_history"
    ESTIMATION_TRACKER_DB = "./estimation_tracker.db"  # SQLite database for estimation results tracking

    # Few-Shot Prompting Configuration
    ENABLE_FEW_SHOT_PROMPTING = True  # Enable/disable historical data usage
    FEW_SHOT_SIMILARITY_THRESHOLD = 0.6  # Minimum similarity score (0-1)
    FEW_SHOT_MAX_EXAMPLES = 5  # Maximum number of historical examples

    @classmethod
    def validate_config(cls):
        """Validate configuration settings"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required. Please set it in your environment or .env file")
        return True
