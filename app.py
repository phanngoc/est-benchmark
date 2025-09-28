import streamlit as st
import os
import json
from datetime import datetime
from typing import List, Dict, Any

# Import local modules
from config import Config
from utils.file_processor import FileProcessor
from utils.graphrag_handler import GraphRAGHandler
from utils.visualization import GraphVisualization

# Page configuration
st.set_page_config(
    page_title=Config.APP_TITLE,
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'graphrag_handler' not in st.session_state:
    st.session_state.graphrag_handler = GraphRAGHandler(Config.WORKING_DIR)
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False

def main():
    """Main application function"""
    
    # Header
    st.title("🧠 " + Config.APP_TITLE)
    st.markdown(f"**{Config.APP_DESCRIPTION}**")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Cấu hình")
        
        # API Key input
        api_key = st.text_input(
            "OpenAI API Key",
            value=Config.OPENAI_API_KEY,
            type="password",
            help="Nhập API key của bạn từ OpenAI"
        )
        
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # Domain configuration
        st.subheader("📝 Cấu hình Domain")
        domain = st.text_area(
            "Mô tả domain:",
            value=Config.DEFAULT_DOMAIN,
            height=100,
            help="Mô tả lĩnh vực và mục tiêu phân tích tài liệu"
        )
        
        # Entity types
        st.subheader("🏷️ Entity Types")
        entity_types_input = st.text_area(
            "Các loại thực thể (mỗi dòng một loại):",
            value="\n".join(Config.DEFAULT_ENTITY_TYPES),
            height=150,
            help="Các loại thực thể mà bạn muốn GraphRAG nhận diện"
        )
        entity_types = [t.strip() for t in entity_types_input.split('\n') if t.strip()]
        
        # Example queries
        st.subheader("❓ Example Queries")
        example_queries_input = st.text_area(
            "Các câu hỏi mẫu (mỗi dòng một câu hỏi):",
            value="\n".join(Config.DEFAULT_EXAMPLE_QUERIES),
            height=150,
            help="Các câu hỏi mẫu để GraphRAG hiểu cách trả lời"
        )
        example_queries = [q.strip() for q in example_queries_input.split('\n') if q.strip()]
        
        # Initialize GraphRAG button
        if st.button("🚀 Khởi tạo GraphRAG", type="primary"):
            with st.spinner("Đang khởi tạo GraphRAG..."):
                success = st.session_state.graphrag_handler.initialize(
                    domain=domain,
                    entity_types=entity_types,
                    example_queries=example_queries
                )
                if success:
                    st.success("✅ GraphRAG đã được khởi tạo thành công!")
                else:
                    st.error("❌ Lỗi khi khởi tạo GraphRAG")
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs(["📁 Upload Files", "🔍 Query", "📊 Visualization", "ℹ️ Info"])
    
    with tab1:
        st.header("📁 Upload và Xử lý Tài liệu")
        
        # File upload
        uploaded_files = st.file_uploader(
            "Chọn tài liệu để phân tích",
            type=['txt', 'pdf', 'docx', 'md'],
            accept_multiple_files=True,
            help="Hỗ trợ: TXT, PDF, DOCX, MD (tối đa 200MB mỗi file)"
        )
        
        if uploaded_files:
            # Process files
            if st.button("🔄 Xử lý Files", type="primary"):
                with st.spinner("Đang xử lý files..."):
                    processed_files = FileProcessor.process_uploaded_files(uploaded_files)
                    st.session_state.processed_files = processed_files
                    
                    if processed_files:
                        st.success(f"✅ Đã xử lý thành công {len(processed_files)} files!")
                        
                        # Show file info
                        st.subheader("📋 Thông tin Files")
                        for file_info in processed_files:
                            with st.expander(f"📄 {file_info['name']} ({file_info['size_mb']:.1f}MB)"):
                                preview = FileProcessor.get_file_preview(file_info['content'])
                                st.text(preview)
        
        # Show processed files
        if st.session_state.processed_files:
            st.subheader("📚 Files đã xử lý")
            
            # File statistics
            total_size = sum(f['size_mb'] for f in st.session_state.processed_files)
            file_types = {}
            for f in st.session_state.processed_files:
                file_type = f['type']
                file_types[file_type] = file_types.get(file_type, 0) + 1
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Tổng số files", len(st.session_state.processed_files))
            with col2:
                st.metric("Tổng dung lượng", f"{total_size:.1f} MB")
            with col3:
                st.metric("Loại files", len(file_types))
            
            # Insert into GraphRAG
            if st.session_state.graphrag_handler.is_initialized:
                if st.button("📥 Thêm vào GraphRAG", type="primary"):
                    with st.spinner("Đang thêm tài liệu vào GraphRAG..."):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        def progress_callback(current, total, message):
                            progress_bar.progress(current / total)
                            status_text.text(message)
                        
                        success = st.session_state.graphrag_handler.insert_documents(
                            st.session_state.processed_files,
                            progress_callback
                        )
                        
                        if success:
                            st.success("✅ Đã thêm tài liệu vào GraphRAG thành công!")
                        else:
                            st.error("❌ Lỗi khi thêm tài liệu vào GraphRAG")
            else:
                st.warning("⚠️ Vui lòng khởi tạo GraphRAG trước khi thêm tài liệu")
    
    with tab2:
        st.header("🔍 Truy vấn GraphRAG")
        
        if not st.session_state.graphrag_handler.is_initialized:
            st.warning("⚠️ Vui lòng khởi tạo GraphRAG trước khi truy vấn")
        else:
            # Query input
            query = st.text_input(
                "Nhập câu hỏi của bạn:",
                placeholder="Ví dụ: Tài liệu này nói về chủ đề gì?",
                help="Nhập câu hỏi để tìm kiếm thông tin từ tài liệu đã xử lý"
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                with_references = st.checkbox("Hiển thị references", value=True)
            
            with col2:
                if st.button("🔍 Tìm kiếm", type="primary"):
                    if query:
                        with st.spinner("Đang tìm kiếm..."):
                            result = st.session_state.graphrag_handler.query(
                                query, 
                                with_references=with_references
                            )
                            
                            if result:
                                # Add to query history
                                st.session_state.query_history.append(result)
                                
                                # Display result
                                st.subheader("💡 Kết quả")
                                st.write(result['response'])
                                
                                # Display references if available
                                if with_references and result.get('references'):
                                    references_html = GraphVisualization.create_references_display(
                                        result['references']
                                    )
                                    st.markdown(references_html, unsafe_allow_html=True)
                            else:
                                st.error("❌ Không thể thực hiện truy vấn")
                    else:
                        st.warning("⚠️ Vui lòng nhập câu hỏi")
            
            # Query history
            if st.session_state.query_history:
                st.subheader("📜 Lịch sử Truy vấn")
                
                # Create query history table
                history_df = GraphVisualization.create_query_results_table(
                    st.session_state.query_history
                )
                st.dataframe(history_df, use_container_width=True)
                
                # Clear history button
                if st.button("🗑️ Xóa lịch sử"):
                    st.session_state.query_history = []
                    st.rerun()
    
    with tab3:
        st.header("📊 Visualization")
        
        if not st.session_state.graphrag_handler.is_initialized:
            st.warning("⚠️ Vui lòng khởi tạo GraphRAG và thêm tài liệu trước khi xem visualization")
        else:
            # Get graph info
            graph_info = st.session_state.graphrag_handler.get_graph_info()
            
            if graph_info:
                st.subheader("📈 Thống kê Graph")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Trạng thái", "✅ Đã khởi tạo" if graph_info.get('is_initialized') else "❌ Chưa khởi tạo")
                with col2:
                    st.metric("Working Directory", graph_info.get('working_dir', 'N/A'))
                with col3:
                    st.metric("Cập nhật cuối", graph_info.get('timestamp', 'N/A')[:19] if graph_info.get('timestamp') else 'N/A')
                
                # File processing stats
                if st.session_state.processed_files:
                    file_types = {}
                    for f in st.session_state.processed_files:
                        file_type = f['type']
                        file_types[file_type] = file_types.get(file_type, 0) + 1
                    
                    stats = {'file_types': file_types}
                    fig = GraphVisualization.create_processing_stats(stats)
                    if fig.data:
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("ℹ️ Chưa có dữ liệu để hiển thị")
    
    with tab4:
        st.header("ℹ️ Thông tin Ứng dụng")
        
        st.markdown("""
        ### 🧠 Fast GraphRAG Document Analyzer
        
        Ứng dụng này sử dụng **Fast GraphRAG** để phân tích và truy vấn tài liệu một cách thông minh.
        
        #### ✨ Tính năng chính:
        - 📁 **Upload đa dạng loại file**: TXT, PDF, DOCX, MD
        - 🧠 **Phân tích thông minh**: Sử dụng GraphRAG để tạo knowledge graph
        - 🔍 **Truy vấn tự nhiên**: Hỏi đáp bằng tiếng Việt
        - 📊 **Visualization**: Hiển thị mối quan hệ giữa các thực thể
        - 📜 **Lịch sử truy vấn**: Lưu trữ và quản lý các câu hỏi đã hỏi
        
        #### 🚀 Cách sử dụng:
        1. **Cấu hình**: Nhập OpenAI API key và thiết lập domain
        2. **Upload**: Chọn và upload các file tài liệu
        3. **Xử lý**: Thêm tài liệu vào GraphRAG
        4. **Truy vấn**: Đặt câu hỏi và nhận câu trả lời thông minh
        5. **Visualization**: Xem biểu đồ và thống kê
        
        #### 🔧 Cấu hình:
        - **Domain**: Mô tả lĩnh vực và mục tiêu phân tích
        - **Entity Types**: Các loại thực thể cần nhận diện
        - **Example Queries**: Câu hỏi mẫu để hướng dẫn AI
        
        #### 📚 Dependencies:
        - Fast GraphRAG: Framework chính
        - OpenAI: Language model
        - Streamlit: Web interface
        - Plotly: Visualization
        - NetworkX: Graph processing
        """)
        
        # System info
        st.subheader("🔧 Thông tin Hệ thống")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **Cấu hình:**
            - Working Directory: `{Config.WORKING_DIR}`
            - Max File Size: {Config.MAX_FILE_SIZE / (1024*1024):.0f}MB
            - Supported Extensions: {', '.join(Config.ALLOWED_EXTENSIONS)}
            """)
        
        with col2:
            st.markdown(f"""
            **Trạng thái:**
            - GraphRAG Initialized: {'✅' if st.session_state.graphrag_handler.is_initialized else '❌'}
            - Files Processed: {len(st.session_state.processed_files)}
            - Queries Made: {len(st.session_state.query_history)}
            """)

if __name__ == "__main__":
    main()
