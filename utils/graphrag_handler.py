import os
import streamlit as st
from typing import List, Dict, Any, Optional
from fast_graphrag import GraphRAG
import json
from datetime import datetime

class GraphRAGHandler:
    """Wrapper class để quản lý Fast GraphRAG"""
    
    def __init__(self, working_dir: str = "./graphrag_workspace"):
        self.working_dir = working_dir
        self.graphrag = None
        self.is_initialized = False
        
        # Tạo working directory nếu chưa có
        os.makedirs(working_dir, exist_ok=True)
    
    def initialize(self, domain: str, entity_types: List[str], example_queries: List[str]) -> bool:
        """Khởi tạo GraphRAG với cấu hình"""
        try:
            self.graphrag = GraphRAG(
                working_dir=self.working_dir,
                domain=domain,
                entity_types=entity_types,
                example_queries="\n".join(example_queries)
            )
            self.is_initialized = True
            return True
        except Exception as e:
            st.error(f"Lỗi khi khởi tạo GraphRAG: {str(e)}")
            return False
    
    def insert_documents(self, documents: List[Dict[str, Any]], progress_callback=None) -> bool:
        """Thêm tài liệu vào GraphRAG"""
        if not self.is_initialized:
            st.error("GraphRAG chưa được khởi tạo")
            return False
        
        try:
            total_docs = len(documents)
            for i, doc in enumerate(documents):
                if progress_callback:
                    progress_callback(i, total_docs, f"Đang xử lý: {doc['name']}")
                
                # Thêm document vào GraphRAG
                self.graphrag.insert(doc['content'])
                
                # Log progress
                st.write(f"✅ Đã xử lý: {doc['name']} ({doc['size_mb']:.1f}MB)")
            
            if progress_callback:
                progress_callback(total_docs, total_docs, "Hoàn thành!")
            
            return True
            
        except Exception as e:
            st.error(f"Lỗi khi thêm tài liệu: {str(e)}")
            return False
    
    def query(self, query: str, with_references: bool = True) -> Optional[Dict[str, Any]]:
        """Thực hiện query trên GraphRAG"""
        if not self.is_initialized:
            st.error("GraphRAG chưa được khởi tạo")
            return None
        
        try:
            result = self.graphrag.query(query)
            
            return {
                'response': result.response,
                'references': getattr(result, 'references', []) if with_references else [],
                'query': query,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            st.error(f"Lỗi khi thực hiện query: {str(e)}")
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
