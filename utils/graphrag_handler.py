import os
import streamlit as st
from typing import List, Dict, Any, Optional
from fast_graphrag import GraphRAG
import json
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from utils.logger import get_logger

logger = get_logger(__name__)

def validate_openai_api_key() -> bool:
    """Validate OpenAI API key exists and has correct format"""
    api_key = os.environ.get("OPENAI_API_KEY", "")

    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment")
        return False

    if not api_key.startswith("sk-"):
        logger.error(f"Invalid OPENAI_API_KEY format (should start with 'sk-')")
        return False

    if len(api_key) < 20:
        logger.error(f"OPENAI_API_KEY too short (length: {len(api_key)})")
        return False

    logger.info("OpenAI API key validation passed")
    return True

class GraphRAGHandler:
    """Wrapper class để quản lý Fast GraphRAG với project isolation"""
    
    def __init__(self, working_dir: str = "./graphrag_workspace", project_id: Optional[str] = None):
        """
        Initialize GraphRAG handler with optional project isolation
        
        Args:
            working_dir: Base working directory for GraphRAG
            project_id: Optional project ID for isolated workspace. 
                       If provided, creates project-specific subdirectory.
        """
        self.base_working_dir = working_dir
        self.project_id = project_id
        
        # Construct project-specific working directory
        if project_id:
            self.working_dir = os.path.join(working_dir, project_id)
            logger.info(f"Project-scoped GraphRAG: project_id={project_id}")
        else:
            self.working_dir = working_dir
            logger.info("Global GraphRAG workspace (no project_id)")
        
        self.graphrag = None
        self.is_initialized = False

        # Tạo working directory nếu chưa có
        os.makedirs(self.working_dir, exist_ok=True)
        logger.info(f"GraphRAGHandler initialized with working_dir: {self.working_dir}")
    
    def initialize(self, domain: str, entity_types: List[str], example_queries: List[str]) -> bool:
        """
        Khởi tạo GraphRAG với cấu hình trong project-specific workspace
        
        Args:
            domain: Domain description for GraphRAG
            entity_types: List of entity types to extract
            example_queries: Example queries for GraphRAG
            
        Returns:
            True if initialization successful, False otherwise
        """
        # Validate API key first
        if not validate_openai_api_key():
            st.error("❌ Invalid or missing OPENAI_API_KEY. Please check your .env file.")
            return False

        try:
            # Ensure project-specific directory exists
            os.makedirs(self.working_dir, exist_ok=True)
            
            if self.project_id:
                logger.info(f"Initializing GraphRAG for project: {self.project_id}")
                logger.info(f"Project workspace: {self.working_dir}")
            else:
                logger.info(f"Initializing GraphRAG with domain: {domain}")
            
            logger.debug(f"Entity types: {entity_types}")
            logger.debug(f"Working directory: {self.working_dir}")
            
            self.graphrag = GraphRAG(
                working_dir=self.working_dir,
                domain=domain,
                entity_types=entity_types,
                example_queries="\n".join(example_queries)
            )
            self.is_initialized = True
            
            if self.project_id:
                logger.info(f"GraphRAG initialized successfully for project: {self.project_id}")
            else:
                logger.info("GraphRAG initialized successfully")
            
            return True
        except Exception as e:
            st.error(f"Lỗi khi khởi tạo GraphRAG: {str(e)}")
            logger.error(f"Failed to initialize GraphRAG: {str(e)}")
            logger.exception(e)
            return False

    def _insert_sync(self, content: str):
        """Synchronous insert wrapper - disable tqdm to avoid stderr pipe issues in Streamlit"""
        return self.graphrag.insert(content, show_progress=False)
    
    def insert_documents(self, documents: List[Dict[str, Any]], progress_callback=None) -> bool:
        """
        Thêm tài liệu vào GraphRAG với async wrapper để tránh event loop conflict
        Documents are inserted into project-specific workspace if project_id is set
        
        Args:
            documents: List of document dictionaries with 'name' and 'content' keys
            progress_callback: Optional callback function for progress updates
            
        Returns:
            True if insertion successful, False otherwise
        """
        if not self.is_initialized:
            st.error("GraphRAG chưa được khởi tạo")
            logger.error("Attempted to insert documents without GraphRAG initialization")
            return False

        try:
            total_docs = len(documents)
            if self.project_id:
                logger.info(f"Starting document insertion for project {self.project_id}: {total_docs} documents")
            else:
                logger.info(f"Starting document insertion: {total_docs} documents")

            # Get or create event loop for Streamlit context
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            for i, doc in enumerate(documents):
                if progress_callback:
                    progress_callback(i, total_docs, f"Đang xử lý: {doc['name']}")

                logger.debug(f"Inserting document {i+1}/{total_docs}: {doc['name']}")
                logger.debug(f"Document content preview: {doc['content'][:100]}...")

                # Run insert in thread pool to avoid blocking event loop
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = loop.run_in_executor(executor, self._insert_sync, doc['content'])
                    # Wait for completion without blocking
                    loop.run_until_complete(asyncio.wait_for(future, timeout=300))  # 5 min timeout

                # Log progress
                st.write(f"✅ Đã xử lý: {doc['name']}")
                logger.debug(f"Processed document {i+1}/{total_docs}: {doc['name']}")

            if progress_callback:
                progress_callback(total_docs, total_docs, "Hoàn thành!")

            if self.project_id:
                logger.info(f"Successfully inserted {total_docs} documents into GraphRAG for project {self.project_id}")
            else:
                logger.info(f"Successfully inserted {total_docs} documents into GraphRAG")
            return True

        except asyncio.TimeoutError:
            error_msg = "Document insertion timeout (exceeded 5 minutes)"
            st.error(f"❌ {error_msg}")
            logger.error(error_msg)
            return False
        except Exception as e:
            st.error(f"Lỗi khi thêm tài liệu: {str(e)}")
            logger.error(f"Error inserting documents: {str(e)}")
            logger.exception(e)
            return False
    
    def query(self, query: str, with_references: bool = True) -> Optional[Dict[str, Any]]:
        """
        Thực hiện query trên GraphRAG trong project-specific workspace
        
        Args:
            query: Query string to execute
            with_references: Include references in response
            
        Returns:
            Dictionary with response, references, query, and timestamp
        """
        if not self.is_initialized:
            st.error("GraphRAG chưa được khởi tạo")
            logger.error("Attempted query without GraphRAG initialization")
            return None

        try:
            if self.project_id:
                logger.debug(f"Executing GraphRAG query for project {self.project_id}: {query[:100]}...")
            else:
                logger.debug(f"Executing GraphRAG query: {query[:100]}...")
            
            result = self.graphrag.query(query)

            if self.project_id:
                logger.info(f"Query executed successfully for project {self.project_id}: {query[:50]}...")
            else:
                logger.info(f"Query executed successfully: {query[:50]}...")
            
            return {
                'response': result.response,
                'references': getattr(result, 'references', []) if with_references else [],
                'query': query,
                'project_id': self.project_id,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            st.error(f"Lỗi khi thực hiện query: {str(e)}")
            logger.error(f"Query execution failed: {str(e)}")
            logger.exception(e)
            return None
    
    def get_graph_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin về graph hiện tại
        Includes project_id if this is a project-scoped instance
        """
        if not self.is_initialized:
            return {}
        
        try:
            # Lấy thông tin cơ bản về graph
            # Note: Fast GraphRAG có thể không expose trực tiếp graph info
            # Có thể cần implement thêm methods để lấy graph statistics
            info = {
                'working_dir': self.working_dir,
                'is_initialized': self.is_initialized,
                'timestamp': datetime.now().isoformat()
            }
            
            if self.project_id:
                info['project_id'] = self.project_id
                info['base_working_dir'] = self.base_working_dir
            
            return info
        except Exception as e:
            st.error(f"Lỗi khi lấy thông tin graph: {str(e)}")
            logger.error(f"Failed to get graph info: {str(e)}")
            return {}
    
    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """Lưu session data"""
        try:
            session_file = os.path.join(self.working_dir, "session_data.json")
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"Lỗi khi lưu session: {str(e)}")
            return False
    
    def load_session(self) -> Optional[Dict[str, Any]]:
        """Load session data"""
        try:
            session_file = os.path.join(self.working_dir, "session_data.json")
            if os.path.exists(session_file):
                with open(session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            st.error(f"Lỗi khi load session: {str(e)}")
            return None
    
    def reset(self) -> bool:
        """Reset GraphRAG instance"""
        try:
            self.graphrag = None
            self.is_initialized = False
            return True
        except Exception as e:
            st.error(f"Lỗi khi reset: {str(e)}")
            return False
