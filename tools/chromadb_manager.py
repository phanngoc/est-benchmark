"""
ChromaDB Manager Tool - Quản lý ChromaDB với giao diện Streamlit
Tính năng: Create, Query, Update, Delete collections và documents
"""
import streamlit as st
import chromadb
from chromadb.config import Settings
import json
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Page config
st.set_page_config(
    page_title="ChromaDB Manager",
    page_icon="🗄️",
    layout="wide"
)


class ChromaDBManager:
    """Wrapper class để quản lý ChromaDB"""
    
    def __init__(self, db_path: str):
        """Initialize ChromaDB client"""
        self.db_path = db_path
        try:
            self.client = chromadb.PersistentClient(
                path=db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            self.connected = True
        except Exception as e:
            st.error(f"❌ Không thể kết nối ChromaDB: {str(e)}")
            self.connected = False
            self.client = None
    
    def list_collections(self) -> List[str]:
        """Liệt kê tất cả collections"""
        if not self.connected:
            return []
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            st.error(f"Lỗi khi liệt kê collections: {str(e)}")
            return []
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Lấy thông tin chi tiết về collection"""
        if not self.connected:
            return {}
        try:
            collection = self.client.get_collection(collection_name)
            count = collection.count()
            metadata = collection.metadata
            return {
                "name": collection_name,
                "count": count,
                "metadata": metadata
            }
        except Exception as e:
            st.error(f"Lỗi khi lấy thông tin collection: {str(e)}")
            return {}
    
    def create_collection(self, name: str, metadata: Optional[Dict] = None) -> bool:
        """Tạo collection mới"""
        if not self.connected:
            return False
        try:
            self.client.create_collection(
                name=name,
                metadata=metadata or {}
            )
            return True
        except Exception as e:
            st.error(f"Lỗi khi tạo collection: {str(e)}")
            return False
    
    def delete_collection(self, name: str) -> bool:
        """Xóa collection"""
        if not self.connected:
            return False
        try:
            self.client.delete_collection(name)
            return True
        except Exception as e:
            st.error(f"Lỗi khi xóa collection: {str(e)}")
            return False
    
    def query_collection(
        self,
        collection_name: str,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Query collection"""
        if not self.connected:
            return {}
        try:
            collection = self.client.get_collection(collection_name)
            results = collection.query(
                query_texts=query_texts,
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
                where_document=where_document
            )
            return results
        except Exception as e:
            st.error(f"Lỗi khi query: {str(e)}")
            return {}
    
    def get_all_documents(self, collection_name: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Lấy tất cả documents từ collection"""
        if not self.connected:
            return {}
        try:
            collection = self.client.get_collection(collection_name)
            results = collection.get(limit=limit)
            return results
        except Exception as e:
            st.error(f"Lỗi khi lấy documents: {str(e)}")
            return {}
    
    def add_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> bool:
        """Thêm documents vào collection"""
        if not self.connected:
            return False
        try:
            collection = self.client.get_collection(collection_name)
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            return True
        except Exception as e:
            st.error(f"Lỗi khi thêm documents: {str(e)}")
            return False
    
    def update_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> bool:
        """Update documents trong collection"""
        if not self.connected:
            return False
        try:
            collection = self.client.get_collection(collection_name)
            collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            return True
        except Exception as e:
            st.error(f"Lỗi khi update documents: {str(e)}")
            return False
    
    def delete_documents(self, collection_name: str, ids: List[str]) -> bool:
        """Xóa documents từ collection"""
        if not self.connected:
            return False
        try:
            collection = self.client.get_collection(collection_name)
            collection.delete(ids=ids)
            return True
        except Exception as e:
            st.error(f"Lỗi khi xóa documents: {str(e)}")
            return False


def render_collection_management(db_manager: ChromaDBManager):
    """Render giao diện quản lý collections"""
    st.header("📚 Quản lý Collections")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Danh sách Collections")
        collections = db_manager.list_collections()
        
        if collections:
            for col_name in collections:
                col_info = db_manager.get_collection_info(col_name)
                with st.expander(f"📁 {col_name} ({col_info.get('count', 0)} documents)"):
                    st.json(col_info.get('metadata', {}))
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button(f"🔍 Xem chi tiết", key=f"view_{col_name}"):
                            st.session_state.selected_collection = col_name
                            st.session_state.active_tab = "documents"
                    with col_b:
                        if st.button(f"🗑️ Xóa", key=f"delete_{col_name}", type="secondary"):
                            if st.session_state.get(f"confirm_delete_{col_name}"):
                                if db_manager.delete_collection(col_name):
                                    st.success(f"✅ Đã xóa collection: {col_name}")
                                    st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{col_name}"] = True
                                st.warning("⚠️ Click lại để xác nhận xóa!")
        else:
            st.info("📭 Chưa có collection nào. Hãy tạo collection mới!")
    
    with col2:
        st.subheader("Tạo Collection Mới")
        new_col_name = st.text_input("Tên collection:", key="new_collection_name")
        new_col_desc = st.text_area("Mô tả (metadata):", key="new_collection_desc")
        
        if st.button("➕ Tạo Collection", type="primary"):
            if new_col_name:
                metadata = {"description": new_col_desc} if new_col_desc else {}
                if db_manager.create_collection(new_col_name, metadata):
                    st.success(f"✅ Đã tạo collection: {new_col_name}")
                    st.rerun()
            else:
                st.warning("⚠️ Vui lòng nhập tên collection!")


def render_document_management(db_manager: ChromaDBManager, collection_name: str):
    """Render giao diện quản lý documents"""
    st.header(f"📄 Documents trong Collection: {collection_name}")
    
    # Tabs for different operations
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Xem tất cả", "➕ Thêm mới", "✏️ Cập nhật", "🗑️ Xóa"])
    
    with tab1:
        st.subheader("Danh sách Documents")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            limit = st.number_input("Số lượng hiển thị:", min_value=10, max_value=1000, value=100, step=10)
        with col2:
            if st.button("🔄 Refresh", type="secondary"):
                st.rerun()
        
        results = db_manager.get_all_documents(collection_name, limit=limit)
        
        if results and results.get('ids'):
            df_data = []
            for i, doc_id in enumerate(results['ids']):
                row = {
                    'ID': doc_id,
                    'Document': results['documents'][i] if results.get('documents') else '',
                }
                if results.get('metadatas'):
                    metadata = results['metadatas'][i]
                    for key, value in metadata.items():
                        row[key] = value
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, width='stretch', height=400)
            
            # Export to CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export CSV",
                data=csv,
                file_name=f"{collection_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("📭 Collection này chưa có documents nào.")
    
    with tab2:
        st.subheader("Thêm Documents Mới")
        
        add_mode = st.radio("Chọn cách thêm:", ["Single Document", "Batch Import (JSON)"], horizontal=True)
        
        if add_mode == "Single Document":
            doc_id = st.text_input("Document ID:", key="add_doc_id")
            doc_text = st.text_area("Document Content:", height=150, key="add_doc_text")
            
            st.write("**Metadata (JSON format):**")
            metadata_str = st.text_area(
                "Nhập metadata dạng JSON:",
                value='{\n  "key": "value"\n}',
                height=100,
                key="add_metadata"
            )
            
            if st.button("➕ Thêm Document", type="primary"):
                if doc_id and doc_text:
                    try:
                        metadata = json.loads(metadata_str) if metadata_str else {}
                        if db_manager.add_documents(
                            collection_name,
                            ids=[doc_id],
                            documents=[doc_text],
                            metadatas=[metadata]
                        ):
                            st.success(f"✅ Đã thêm document: {doc_id}")
                            st.rerun()
                    except json.JSONDecodeError:
                        st.error("❌ Metadata không đúng định dạng JSON!")
                else:
                    st.warning("⚠️ Vui lòng nhập đầy đủ ID và Content!")
        
        else:  # Batch Import
            st.write("**Định dạng JSON cho batch import:**")
            st.code('''[
  {
    "id": "doc1",
    "document": "Nội dung document 1",
    "metadata": {"key": "value"}
  },
  {
    "id": "doc2",
    "document": "Nội dung document 2",
    "metadata": {"key": "value"}
  }
]''', language="json")
            
            batch_json = st.text_area("Nhập JSON array:", height=300, key="batch_import")
            
            if st.button("📥 Import Batch", type="primary"):
                try:
                    batch_data = json.loads(batch_json)
                    ids = [item['id'] for item in batch_data]
                    documents = [item['document'] for item in batch_data]
                    metadatas = [item.get('metadata', {}) for item in batch_data]
                    
                    if db_manager.add_documents(
                        collection_name,
                        ids=ids,
                        documents=documents,
                        metadatas=metadatas
                    ):
                        st.success(f"✅ Đã import {len(ids)} documents!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Lỗi import: {str(e)}")
    
    with tab3:
        st.subheader("Cập nhật Document")
        
        # Get list of document IDs
        results = db_manager.get_all_documents(collection_name)
        doc_ids = results.get('ids', [])
        
        if doc_ids:
            selected_id = st.selectbox("Chọn Document ID:", doc_ids, key="update_doc_id")
            
            # Get current document data
            if selected_id:
                idx = doc_ids.index(selected_id)
                current_doc = results['documents'][idx] if results.get('documents') else ''
                current_metadata = results['metadatas'][idx] if results.get('metadatas') else {}
                
                st.write("**Dữ liệu hiện tại:**")
                st.code(current_doc)
                st.json(current_metadata)
                
                st.write("**Dữ liệu mới:**")
                new_doc = st.text_area("Document Content mới:", value=current_doc, height=150, key="update_new_doc")
                new_metadata_str = st.text_area(
                    "Metadata mới (JSON):",
                    value=json.dumps(current_metadata, indent=2, ensure_ascii=False),
                    height=150,
                    key="update_new_metadata"
                )
                
                if st.button("💾 Cập nhật", type="primary"):
                    try:
                        new_metadata = json.loads(new_metadata_str)
                        if db_manager.update_documents(
                            collection_name,
                            ids=[selected_id],
                            documents=[new_doc],
                            metadatas=[new_metadata]
                        ):
                            st.success(f"✅ Đã cập nhật document: {selected_id}")
                            st.rerun()
                    except json.JSONDecodeError:
                        st.error("❌ Metadata không đúng định dạng JSON!")
        else:
            st.info("📭 Collection này chưa có documents nào để cập nhật.")
    
    with tab4:
        st.subheader("Xóa Documents")
        
        results = db_manager.get_all_documents(collection_name)
        doc_ids = results.get('ids', [])
        
        if doc_ids:
            delete_mode = st.radio("Chọn cách xóa:", ["Xóa từng document", "Xóa nhiều documents"], horizontal=True)
            
            if delete_mode == "Xóa từng document":
                selected_id = st.selectbox("Chọn Document ID để xóa:", doc_ids, key="delete_single_id")
                
                if selected_id:
                    # Show document info
                    idx = doc_ids.index(selected_id)
                    if results.get('documents'):
                        st.write("**Document content:**")
                        st.code(results['documents'][idx][:500] + "..." if len(results['documents'][idx]) > 500 else results['documents'][idx])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗑️ Xóa Document", type="secondary"):
                            if db_manager.delete_documents(collection_name, [selected_id]):
                                st.success(f"✅ Đã xóa document: {selected_id}")
                                st.rerun()
            else:
                selected_ids = st.multiselect("Chọn Documents để xóa:", doc_ids, key="delete_multi_ids")
                
                if selected_ids:
                    st.warning(f"⚠️ Bạn sắp xóa {len(selected_ids)} documents!")
                    if st.button(f"🗑️ Xóa {len(selected_ids)} Documents", type="secondary"):
                        if db_manager.delete_documents(collection_name, selected_ids):
                            st.success(f"✅ Đã xóa {len(selected_ids)} documents!")
                            st.rerun()
        else:
            st.info("📭 Collection này chưa có documents nào để xóa.")


def render_query_panel(db_manager: ChromaDBManager, collection_name: str):
    """Render giao diện query semantic search"""
    st.header(f"🔍 Query Panel - Collection: {collection_name}")
    
    query_tab1, query_tab2, query_tab3 = st.tabs(["🔎 Semantic Search", "🎯 Filter by Metadata", "📊 Advanced Query"])
    
    with query_tab1:
        st.subheader("Semantic Search")
        st.write("Tìm kiếm documents tương tự dựa trên nội dung")
        
        query_text = st.text_area("Nhập text để tìm kiếm:", height=100, key="query_semantic")
        n_results = st.slider("Số lượng kết quả:", min_value=1, max_value=50, value=5)
        
        if st.button("🔍 Tìm kiếm", type="primary"):
            if query_text:
                with st.spinner("Đang tìm kiếm..."):
                    results = db_manager.query_collection(
                        collection_name,
                        query_texts=[query_text],
                        n_results=n_results
                    )
                    
                    if results and results.get('ids'):
                        st.success(f"✅ Tìm thấy {len(results['ids'][0])} kết quả!")
                        
                        for i, doc_id in enumerate(results['ids'][0]):
                            distance = results['distances'][0][i] if results.get('distances') else None
                            doc = results['documents'][0][i] if results.get('documents') else ''
                            metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                            
                            with st.expander(f"#{i+1} - {doc_id} (distance: {distance:.4f if distance else 'N/A'})"):
                                st.write("**Document:**")
                                st.text(doc[:1000] + "..." if len(doc) > 1000 else doc)
                                st.write("**Metadata:**")
                                st.json(metadata)
                    else:
                        st.info("📭 Không tìm thấy kết quả nào.")
            else:
                st.warning("⚠️ Vui lòng nhập text để tìm kiếm!")
    
    with query_tab2:
        st.subheader("Filter by Metadata")
        st.write("Lọc documents theo điều kiện metadata")
        
        st.write("**Ví dụ filter:**")
        st.code('''{"category": "Backend"}
{"$and": [{"priority": "High"}, {"status": "pending"}]}
{"$or": [{"category": "Frontend"}, {"category": "Backend"}]}''', language="json")
        
        where_filter = st.text_area(
            "Nhập filter (JSON format):",
            value='{\n  "key": "value"\n}',
            height=150,
            key="query_where"
        )
        
        n_results = st.slider("Số lượng kết quả:", min_value=1, max_value=100, value=10, key="filter_n_results")
        
        if st.button("🎯 Lọc", type="primary"):
            try:
                where = json.loads(where_filter)
                results = db_manager.get_all_documents(collection_name)
                
                # Manual filtering (ChromaDB get doesn't support where clause in basic version)
                filtered_results = []
                if results and results.get('ids'):
                    for i, doc_id in enumerate(results['ids']):
                        metadata = results['metadatas'][i] if results.get('metadatas') else {}
                        # Simple matching
                        match = all(metadata.get(k) == v for k, v in where.items())
                        if match:
                            filtered_results.append({
                                'id': doc_id,
                                'document': results['documents'][i] if results.get('documents') else '',
                                'metadata': metadata
                            })
                
                if filtered_results:
                    st.success(f"✅ Tìm thấy {len(filtered_results)} kết quả!")
                    for i, item in enumerate(filtered_results[:n_results]):
                        with st.expander(f"#{i+1} - {item['id']}"):
                            st.write("**Document:**")
                            st.text(item['document'][:1000] + "..." if len(item['document']) > 1000 else item['document'])
                            st.write("**Metadata:**")
                            st.json(item['metadata'])
                else:
                    st.info("📭 Không tìm thấy kết quả phù hợp.")
            except json.JSONDecodeError:
                st.error("❌ Filter không đúng định dạng JSON!")
    
    with query_tab3:
        st.subheader("Advanced Query")
        st.write("Kết hợp semantic search và metadata filter")
        
        adv_query_text = st.text_area("Query text:", height=100, key="adv_query_text")
        adv_where_filter = st.text_area(
            "Where filter (JSON):",
            value='{}',
            height=100,
            key="adv_where_filter"
        )
        adv_n_results = st.slider("Số kết quả:", min_value=1, max_value=50, value=5, key="adv_n_results")
        
        if st.button("🚀 Query", type="primary"):
            if adv_query_text:
                try:
                    where = json.loads(adv_where_filter) if adv_where_filter and adv_where_filter.strip() != '{}' else None
                    
                    with st.spinner("Đang query..."):
                        results = db_manager.query_collection(
                            collection_name,
                            query_texts=[adv_query_text],
                            n_results=adv_n_results,
                            where=where
                        )
                        
                        if results and results.get('ids'):
                            st.success(f"✅ Tìm thấy {len(results['ids'][0])} kết quả!")
                            
                            # Create DataFrame for better visualization
                            df_data = []
                            for i, doc_id in enumerate(results['ids'][0]):
                                row = {
                                    'Rank': i + 1,
                                    'ID': doc_id,
                                    'Distance': f"{results['distances'][0][i]:.4f}" if results.get('distances') else 'N/A',
                                    'Document': (results['documents'][0][i][:100] + "...") if results.get('documents') and len(results['documents'][0][i]) > 100 else results['documents'][0][i] if results.get('documents') else ''
                                }
                                metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                                for k, v in metadata.items():
                                    row[k] = v
                                df_data.append(row)
                            
                            df = pd.DataFrame(df_data)
                            st.dataframe(df, width='stretch')
                            
                            # Detailed view
                            st.write("**Chi tiết từng kết quả:**")
                            for i, doc_id in enumerate(results['ids'][0]):
                                with st.expander(f"#{i+1} - {doc_id}"):
                                    doc = results['documents'][0][i] if results.get('documents') else ''
                                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                                    
                                    st.write("**Full Document:**")
                                    st.text(doc)
                                    st.write("**Metadata:**")
                                    st.json(metadata)
                        else:
                            st.info("📭 Không tìm thấy kết quả nào.")
                except json.JSONDecodeError:
                    st.error("❌ Filter không đúng định dạng JSON!")
            else:
                st.warning("⚠️ Vui lòng nhập query text!")


def main():
    """Main application"""
    st.title("🗄️ ChromaDB Manager")
    st.markdown("**Quản lý ChromaDB với đầy đủ tính năng CRUD + Query Panel**")
    
    # Initialize session state
    if 'selected_collection' not in st.session_state:
        st.session_state.selected_collection = None
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "collections"
    
    # Sidebar - Database configuration
    with st.sidebar:
        st.header("⚙️ Database Configuration")
        
        # DB Path selector
        st.subheader("📁 Database Path")
        
        default_paths = [
            Config.ESTIMATION_HISTORY_DB_PATH,
            "./chroma_db",
            "./data/chroma"
        ]
        
        custom_path = st.text_input(
            "Custom path:",
            value="",
            help="Nhập đường dẫn tùy chỉnh hoặc chọn từ danh sách"
        )
        
        selected_path = st.selectbox(
            "Hoặc chọn path có sẵn:",
            options=default_paths,
            index=0
        )
        
        db_path = custom_path if custom_path else selected_path
        
        st.info(f"📂 Current DB: `{db_path}`")
        
        # Check if path exists
        if os.path.exists(db_path):
            st.success(f"✅ Database tồn tại")
            db_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, _, filenames in os.walk(db_path)
                for filename in filenames
            )
            st.metric("Database size", f"{db_size / (1024*1024):.2f} MB")
        else:
            st.warning(f"⚠️ Database chưa tồn tại. Sẽ tạo mới khi thêm collection.")
        
        st.divider()
        
        # Navigation
        st.subheader("🧭 Navigation")
        if st.button("📚 Collections", width='stretch'):
            st.session_state.active_tab = "collections"
            st.rerun()
        
        if st.session_state.selected_collection:
            if st.button(f"📄 Documents ({st.session_state.selected_collection})", width='stretch'):
                st.session_state.active_tab = "documents"
                st.rerun()
            
            if st.button(f"🔍 Query Panel ({st.session_state.selected_collection})", width='stretch'):
                st.session_state.active_tab = "query"
                st.rerun()
        
        st.divider()
        
        # Quick stats
        st.subheader("📊 Quick Stats")
        db_manager_temp = ChromaDBManager(db_path)
        if db_manager_temp.connected:
            collections = db_manager_temp.list_collections()
            st.metric("Total Collections", len(collections))
            
            total_docs = sum(
                db_manager_temp.get_collection_info(col).get('count', 0)
                for col in collections
            )
            st.metric("Total Documents", total_docs)
    
    # Main content area
    db_manager = ChromaDBManager(db_path)
    
    if not db_manager.connected:
        st.error("❌ Không thể kết nối đến ChromaDB. Vui lòng kiểm tra lại đường dẫn.")
        return
    
    # Render based on active tab
    if st.session_state.active_tab == "collections":
        render_collection_management(db_manager)
    
    elif st.session_state.active_tab == "documents":
        if st.session_state.selected_collection:
            render_document_management(db_manager, st.session_state.selected_collection)
        else:
            st.warning("⚠️ Vui lòng chọn một collection từ tab Collections!")
            if st.button("← Quay lại Collections"):
                st.session_state.active_tab = "collections"
                st.rerun()
    
    elif st.session_state.active_tab == "query":
        if st.session_state.selected_collection:
            render_query_panel(db_manager, st.session_state.selected_collection)
        else:
            st.warning("⚠️ Vui lòng chọn một collection từ tab Collections!")
            if st.button("← Quay lại Collections"):
                st.session_state.active_tab = "collections"
                st.rerun()


if __name__ == "__main__":
    main()
