import os
import streamlit as st
from typing import List, Dict, Any, Optional
from fast_graphrag import GraphRAG
import json
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

class GraphRAGHandler:
    """Wrapper class để quản lý Fast GraphRAG"""
    
    def __init__(self, working_dir: str = "./graphrag_workspace"):
        self.working_dir = working_dir
        self.graphrag = None
        self.is_initialized = False

        # Tạo working directory nếu chưa có
        os.makedirs(working_dir, exist_ok=True)
        logger.info(f"GraphRAGHandler initialized with working_dir: {working_dir}")
    
    def initialize(self, domain: str, entity_types: List[str], example_queries: List[str]) -> bool:
        """Khởi tạo GraphRAG với cấu hình"""
        try:
            logger.info(f"Initializing GraphRAG with domain: {domain}")
            logger.debug(f"Entity types: {entity_types}")
            self.graphrag = GraphRAG(
                working_dir=self.working_dir,
                domain=domain,
                entity_types=entity_types,
                example_queries="\n".join(example_queries)
            )
            self.is_initialized = True
            logger.info("GraphRAG initialized successfully")
            return True
        except Exception as e:
            st.error(f"Lỗi khi khởi tạo GraphRAG: {str(e)}")
            logger.error(f"Failed to initialize GraphRAG: {str(e)}")
            return False
    
    def insert_documents(self, documents: List[Dict[str, Any]], progress_callback=None) -> bool:
        """Thêm tài liệu vào GraphRAG"""
        if not self.is_initialized:
            st.error("GraphRAG chưa được khởi tạo")
            logger.error("Attempted to insert documents without GraphRAG initialization")
            return False

        try:
            total_docs = len(documents)
            logger.info(f"Starting document insertion: {total_docs} documents")
            for i, doc in enumerate(documents):
                if progress_callback:
                    progress_callback(i, total_docs, f"Đang xử lý: {doc['name']}")
                print(f"Inserting document {i+1}/{total_docs}: {doc['name']} ({doc['size_mb']:.1f}MB)")
                print(f"Content preview: {doc['content'][:100]}...")
                # Thêm document vào GraphRAG
                self.graphrag.insert(doc['content'])

                # Log progress
                st.write(f"✅ Đã xử lý: {doc['name']} ({doc['size_mb']:.1f}MB)")
                logger.debug(f"Processed document {i+1}/{total_docs}: {doc['name']} ({doc['size_mb']:.1f}MB)")

            if progress_callback:
                progress_callback(total_docs, total_docs, "Hoàn thành!")

            logger.info(f"Successfully inserted {total_docs} documents into GraphRAG")
            return True

        except Exception as e:
            print(e)
            st.error(f"Lỗi khi thêm tài liệu: {str(e)}")
            logger.error(f"Error inserting documents: {str(e)}")
            return False
    
    def query(self, query: str, with_references: bool = True) -> Optional[Dict[str, Any]]:
        """Thực hiện query trên GraphRAG"""
        if not self.is_initialized:
            st.error("GraphRAG chưa được khởi tạo")
            logger.error("Attempted query without GraphRAG initialization")
            return None

        try:
            logger.debug(f"Executing GraphRAG query: {query[:100]}...")
            result = self.graphrag.query(query)

            logger.info(f"Query executed successfully: {query[:50]}...")
            return {
                'response': result.response,
                'references': getattr(result, 'references', []) if with_references else [],
                'query': query,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            st.error(f"Lỗi khi thực hiện query: {str(e)}")
            logger.error(f"Query execution failed: {str(e)}")
            return None
    
    def get_graph_info(self) -> Dict[str, Any]:
        """Lấy thông tin về graph hiện tại"""
        if not self.is_initialized:
            return {}
        
        try:
            # Lấy thông tin cơ bản về graph
            # Note: Fast GraphRAG có thể không expose trực tiếp graph info
            # Có thể cần implement thêm methods để lấy graph statistics
            return {
                'working_dir': self.working_dir,
                'is_initialized': self.is_initialized,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            st.error(f"Lỗi khi lấy thông tin graph: {str(e)}")
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
