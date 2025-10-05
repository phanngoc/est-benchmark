import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

# Import local modules
from config import Config
from utils.file_processor import FileProcessor
from utils.graphrag_handler import GraphRAGHandler
from utils.visualization import GraphVisualization
from workflow import EnhancedEstimationWorkflow
from utils.logger import init_logging, get_logger

# Initialize logging system
init_logging(log_dir=Config.LOG_DIR, log_level=Config.LOG_LEVEL)
logger = get_logger(__name__)

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
    # Auto-initialize GraphRAG with default configuration
    if not st.session_state.graphrag_handler.is_initialized:
        logger.info("Auto-initializing GraphRAG on application load")
        success = st.session_state.graphrag_handler.initialize(
            domain=Config.DEFAULT_DOMAIN,
            entity_types=Config.DEFAULT_ENTITY_TYPES,
            example_queries=Config.DEFAULT_EXAMPLE_QUERIES
        )
        if success:
            logger.info("GraphRAG auto-initialized successfully")
        else:
            logger.error("GraphRAG auto-initialization failed")

if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []
if 'show_references' not in st.session_state:
    st.session_state.show_references = True
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False
if 'estimation_workflow' not in st.session_state:
    st.session_state.estimation_workflow = EnhancedEstimationWorkflow()
if 'project_estimation_result' not in st.session_state:
    st.session_state.project_estimation_result = None
if 'estimation_in_progress' not in st.session_state:
    st.session_state.estimation_in_progress = False

def auto_analyze_project_scope(graphrag_handler) -> str:
    """
    Auto-generate comprehensive project description từ uploaded documents
    """
    logger.info("Starting auto_analyze_project_scope")
    if not graphrag_handler or not graphrag_handler.is_initialized:
        logger.warning("GraphRAG handler not initialized for project scope analysis")
        return ""

    # Multiple queries to understand project scope comprehensively
    project_queries = [
        "What is the main project or system described in these documents? Provide a detailed summary.",
        "What are the key features and functionalities that need to be implemented?",
        "What are the technical requirements and components mentioned?",
        "What are the functional and non-functional requirements?",
        "What technologies, frameworks, or platforms are specified?",
        "What are the main modules or subsystems that need to be built?"
    ]

    project_insights = []
    for query in project_queries:
        try:
            result = graphrag_handler.query(query, with_references=False)
            if result and result.get('response'):
                project_insights.append(result['response'])
                logger.debug(f"Project query successful: {query[:50]}...")
        except Exception as e:
            st.warning(f"Could not analyze: {query[:50]}... - {str(e)}")
            logger.error(f"Project query failed: {query[:50]}... - {str(e)}")
            continue

    if not project_insights:
        logger.warning("No project insights gathered from documents")
        return ""

    logger.info(f"Successfully gathered {len(project_insights)} project insights")
    # Combine insights into comprehensive project description
    combined_description = f"""
Phát triển dự án với các yêu cầu sau được trích xuất từ tài liệu:

{chr(10).join([f"- {insight}" for insight in project_insights])}

Dự án cần được chia nhỏ thành các tasks cụ thể với estimation effort phù hợp cho middle developer (3 năm kinh nghiệm).
"""

    return combined_description.strip()

def run_project_estimation():
    """
    Main function để chạy project estimation với Streamlit integration
    """
    logger.info("Starting run_project_estimation")
    if st.session_state.estimation_in_progress:
        st.warning("🔄 Estimation đang chạy. Vui lòng đợi...")
        logger.warning("Estimation already in progress")
        return

    if not st.session_state.graphrag_handler.is_initialized:
        st.error("❌ GraphRAG chưa được khởi tạo. Vui lòng khởi tạo GraphRAG trước.")
        logger.error("Estimation attempted without GraphRAG initialization")
        return

    # Check uploads directory exists and has files
    uploads_check = FileProcessor.check_uploads_directory(Config.UPLOADS_DIR)
    if not uploads_check['exists'] or not uploads_check['has_files']:
        st.error(f"❌ Uploads directory không tồn tại hoặc trống. Vui lòng upload tài liệu trước.")
        logger.error(f"Uploads directory check failed: {uploads_check}")
        return

    try:
        st.session_state.estimation_in_progress = True

        # Step 1: Auto analyze project scope
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("🔍 Đang phân tích tài liệu để hiểu project scope...")
        progress_bar.progress(10)

        project_description = auto_analyze_project_scope(st.session_state.graphrag_handler)

        if not project_description:
            st.error("❌ Không thể phân tích project từ tài liệu. Vui lòng kiểm tra lại tài liệu.")
            logger.error("Failed to analyze project from documents")
            return

        # Display analyzed project description
        with st.expander("📄 Project Description (Analyzed from Documents)", expanded=True):
            st.markdown("**This is the intermediate analysis that will be used as input for the estimation workflow:**")
            st.text_area(
                "Auto-generated Project Scope",
                value=project_description,
                height=300,
                disabled=True,
                key="analyzed_project_desc"
            )
            st.info("💡 This description was automatically generated from your uploaded documents using GraphRAG analysis.")

        # Step 2: Pre-fetch GraphRAG insights to avoid serialization issues
        status_text.text("🔍 Đang pre-fetch GraphRAG insights...")
        progress_bar.progress(20)

        # Pre-fetch additional insights for estimation
        estimation_queries = [
            "What are the main technical challenges mentioned in the project?",
            "What are the integration points and dependencies described?",
            "What are the performance and scalability requirements?",
            "What are the security and compliance requirements mentioned?"
        ]

        graphrag_insights = []
        for query in estimation_queries:
            try:
                result_insight = st.session_state.graphrag_handler.query(query, with_references=False)
                if result_insight and result_insight.get('response'):
                    graphrag_insights.append({
                        'query': query,
                        'response': result_insight['response']
                    })
            except Exception as e:
                st.warning(f"Could not fetch insight for: {query[:50]}...")

        # Step 3: Run estimation workflow
        status_text.text("🚀 Đang chạy estimation workflow...")
        progress_bar.progress(50)

        logger.info("Running estimation workflow with project description and GraphRAG insights")
        result = st.session_state.estimation_workflow.run_estimation(
            project_description,
            graphrag_insights=graphrag_insights
        )

        if result and result.get('workflow_status') == 'completed':
            status_text.text("✅ Estimation hoàn thành!")
            progress_bar.progress(100)

            st.session_state.project_estimation_result = result
            st.success("🎉 Project estimation đã hoàn thành thành công!")
            logger.info(f"Estimation completed successfully: {result.get('total_effort', 0):.1f} mandays")

            # Display summary
            total_effort = result.get('total_effort', 0)
            total_confidence = result.get('total_confidence', 0)
            task_count = len(result.get('final_estimation_data', []))

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Effort", f"{total_effort:.1f} mandays")
            with col2:
                st.metric("Total Tasks", task_count)
            with col3:
                st.metric("Avg Confidence", f"{total_confidence:.0%}")

        else:
            st.error("❌ Estimation workflow failed. Vui lòng thử lại.")
            logger.error(f"Estimation workflow failed with status: {result.get('workflow_status', 'unknown')}")

    except Exception as e:
        st.error(f"❌ Lỗi khi chạy estimation: {str(e)}")
        logger.exception(f"Exception during estimation: {str(e)}")
    finally:
        st.session_state.estimation_in_progress = False
        logger.info("Estimation process completed")

def get_formatted_file_size(file_info: Dict[str, Any]) -> str:
    """Get formatted file size with backward compatibility"""
    if 'size_formatted' in file_info:
        return file_info['size_formatted']
    elif 'size_bytes' in file_info:
        return FileProcessor.format_file_size(file_info['size_bytes'])
    else:
        # Old format with only size_mb
        size_bytes = int(file_info['size_mb'] * 1024 * 1024)
        return FileProcessor.format_file_size(size_bytes)

def main():
    """Main application function"""
    logger.info("="*60)
    logger.info("Fast GraphRAG Document Analyzer - Application Started")
    logger.info("="*60)

    # Header
    st.title("🧠 " + Config.APP_TITLE)
    st.markdown(f"**{Config.APP_DESCRIPTION}**")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Cấu hình")

        # System Status Indicator
        st.markdown("### 📊 System Status")
        if st.session_state.graphrag_handler.is_initialized:
            st.success("🟢 GraphRAG: Ready")
        else:
            st.error("🔴 GraphRAG: Not Initialized")

        st.divider()

        # API Key input
        api_key = st.text_input(
            "OpenAI API Key",
            value=Config.OPENAI_API_KEY,
            type="password",
            help="Nhập API key của bạn từ OpenAI (hoặc để trống để dùng từ .env file)"
        )
        
        # Use API key from input or fall back to config
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        elif Config.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = Config.OPENAI_API_KEY

        # Show API key status
        if Config.OPENAI_API_KEY:
            st.success("✅ API Key loaded from .env file")
        else:
            st.warning("⚠️ No API Key found in .env file")
        
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

        # Re-initialize GraphRAG button (for custom configuration)
        if st.session_state.graphrag_handler.is_initialized:
            st.info("ℹ️ GraphRAG đã được khởi tạo tự động. Bạn có thể cấu hình lại nếu muốn.")
            button_label = "🔄 Re-initialize với cấu hình mới"
            button_type = "secondary"
        else:
            st.warning("⚠️ Auto-initialization failed. Vui lòng thử khởi tạo thủ công.")
            button_label = "🚀 Khởi tạo GraphRAG"
            button_type = "primary"

        if st.button(button_label, type=button_type):
            with st.spinner("Đang khởi tạo GraphRAG..."):
                logger.info(f"Manual GraphRAG initialization requested")
                success = st.session_state.graphrag_handler.initialize(
                    domain=domain,
                    entity_types=entity_types,
                    example_queries=example_queries
                )
                if success:
                    st.success("✅ GraphRAG đã được khởi tạo thành công!")
                    logger.info("Manual GraphRAG initialization successful")
                else:
                    st.error("❌ Lỗi khi khởi tạo GraphRAG")
                    logger.error("Manual GraphRAG initialization failed")

    # Chat controls in sidebar
    st.sidebar.divider()
    st.sidebar.subheader("💬 Chat Settings")
    st.session_state.show_references = st.sidebar.checkbox(
        "Hiển thị references",
        value=st.session_state.show_references,
        key="ref_toggle"
    )
    if st.sidebar.button("🗑️ Clear Chat", key="clear_chat"):
        st.session_state.chat_messages = []
        st.rerun()

    # Main content area
    tab1, tab2, tab3 = st.tabs(["📁 Upload Files", "🔍 Query", "📋 Project Estimation"])
    
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
                    result = FileProcessor.process_uploaded_files(
                        uploaded_files,
                        save_to_disk=True,
                        uploads_dir=Config.UPLOADS_DIR,
                        metadata_file=Config.METADATA_FILE,
                        hash_algorithm=Config.HASH_ALGORITHM
                    )

                    processed_files = result['processed_files']
                    stats = result['stats']
                    duplicates = result['duplicates']

                    st.session_state.processed_files = processed_files

                    # Show statistics
                    st.subheader("📊 Upload Summary")
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("✅ New Files", stats['new'])
                    with col2:
                        st.metric("🔄 Updated Files", stats['updated'])
                    with col3:
                        st.metric("⏭️ Duplicates Skipped", stats['duplicates'])
                    with col4:
                        st.metric("❌ Errors", stats['errors'])

                    # Show success message
                    if processed_files:
                        total_processed = stats['new'] + stats['updated']
                        st.success(f"✅ Đã xử lý thành công {total_processed} files!")

                        # Show duplicate warnings if any
                        if duplicates:
                            st.warning(f"⚠️ {len(duplicates)} file(s) bị bỏ qua do trùng lặp:")
                            for dup in duplicates:
                                dup_type_icon = "📝" if dup['type'] == 'exact' else "🔄"
                                st.caption(f"{dup_type_icon} **{dup['name']}** - {dup['message']}")

                        # Show file info
                        st.subheader("📋 Thông tin Files")
                        for file_info in processed_files:
                            status_icon = "🆕" if file_info['status'] == 'new' else "🔄"
                            with st.expander(f"{status_icon} {file_info['name']} ({file_info['size_formatted']}) - Hash: {file_info['hash']}"):
                                st.caption(f"**Status**: {file_info['status'].upper()}")
                                st.caption(f"**Hash**: `{file_info['hash_full']}`")
                                preview = FileProcessor.get_file_preview(file_info['content'])
                                st.text(preview)
                    else:
                        st.info("ℹ️ Không có file mới nào được xử lý.")
        
        # Show processed files
        if st.session_state.processed_files:
            st.subheader("📚 Files đã xử lý")
            
            # File statistics
            # Backward compatibility: calculate size_bytes from size_mb if not present
            total_size_bytes = 0
            for f in st.session_state.processed_files:
                if 'size_bytes' in f:
                    total_size_bytes += f['size_bytes']
                else:
                    # Convert from MB to bytes for old format
                    total_size_bytes += int(f['size_mb'] * 1024 * 1024)

            file_types = {}
            for f in st.session_state.processed_files:
                file_type = f['type']
                file_types[file_type] = file_types.get(file_type, 0) + 1

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Tổng số files", len(st.session_state.processed_files))
            with col2:
                st.metric("Tổng dung lượng", FileProcessor.format_file_size(total_size_bytes))
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
            # Welcome message for empty chat
            if not st.session_state.chat_messages:
                st.info("👋 Xin chào! Hãy đặt câu hỏi về tài liệu đã upload.")

            # Display chat history
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

                    # Show references if available (for assistant messages)
                    if message["role"] == "assistant" and message.get("references"):
                        with st.expander("📚 Nguồn tham khảo"):
                            references_html = GraphVisualization.create_references_display(
                                message["references"]
                            )
                            st.markdown(references_html, unsafe_allow_html=True)

            # Chat input
            if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
                # Add user message to chat
                st.session_state.chat_messages.append({
                    "role": "user",
                    "content": prompt,
                    "timestamp": datetime.now().isoformat()
                })

                # Display user message immediately
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Query GraphRAG and show assistant response
                with st.chat_message("assistant"):
                    with st.spinner("Đang tìm kiếm..."):
                        result = st.session_state.graphrag_handler.query(
                            prompt,
                            with_references=st.session_state.show_references
                        )

                        if result:
                            # Display response
                            st.markdown(result['response'])

                            # Add to chat history
                            st.session_state.chat_messages.append({
                                "role": "assistant",
                                "content": result['response'],
                                "references": result.get('references', []) if st.session_state.show_references else [],
                                "timestamp": datetime.now().isoformat()
                            })

                            # Show references if available
                            if st.session_state.show_references and result.get('references'):
                                with st.expander("📚 Nguồn tham khảo"):
                                    references_html = GraphVisualization.create_references_display(
                                        result['references']
                                    )
                                    st.markdown(references_html, unsafe_allow_html=True)
                        else:
                            error_msg = "❌ Không thể thực hiện truy vấn"
                            st.error(error_msg)
                            st.session_state.chat_messages.append({
                                "role": "assistant",
                                "content": error_msg,
                                "timestamp": datetime.now().isoformat()
                            })

    with tab3:
        st.header("📋 Project Estimation")

        # Check uploads directory
        uploads_check = FileProcessor.check_uploads_directory(Config.UPLOADS_DIR)

        # Prerequisites check section
        st.subheader("🔍 Prerequisites Check")
        col1, col2, col3 = st.columns(3)

        with col1:
            graphrag_status = "✅ Initialized" if st.session_state.graphrag_handler.is_initialized else "❌ Not Initialized"
            st.metric("GraphRAG Status", graphrag_status)

        with col2:
            files_status = f"✅ {uploads_check['file_count']} files" if uploads_check['has_files'] else "❌ No files"
            st.metric("Documents (./uploads)", files_status)

        with col3:
            ready_status = "✅ Ready" if (st.session_state.graphrag_handler.is_initialized and uploads_check['has_files']) else "❌ Not Ready"
            st.metric("Estimation Ready", ready_status)

        st.divider()

        # Main estimation section
        if not st.session_state.graphrag_handler.is_initialized:
            st.warning("⚠️ Vui lòng khởi tạo GraphRAG trước khi thực hiện estimation.")
            st.info("💡 Đi đến tab 'Upload Files' để khởi tạo GraphRAG và upload tài liệu.")
        elif not uploads_check['has_files']:
            st.warning("⚠️ Vui lòng upload và xử lý tài liệu trước khi thực hiện estimation.")
            st.info("💡 Đi đến tab 'Upload Files' để upload tài liệu dự án.")
            if uploads_check['exists']:
                st.caption(f"📁 Uploads directory exists but empty: {Config.UPLOADS_DIR}")
        else:
            # One-click estimation button
            st.subheader("🚀 Auto Project Analysis & Estimation")
            st.markdown("""
            **Chức năng này sẽ:**
            - 🔍 Tự động phân tích toàn bộ tài liệu đã upload
            - 🧠 Sử dụng GraphRAG để hiểu project scope và requirements
            - 📋 Chia nhỏ project thành các tasks cụ thể
            - ⏱️ Estimate effort cho từng task (target: middle developer 3 năm kinh nghiệm)
            - 📊 Tạo báo cáo estimation hoàn chỉnh với Excel export
            """)

            # Big estimation button
            if st.button("🚀 Analyze & Estimate Project", type="primary", disabled=st.session_state.estimation_in_progress):
                run_project_estimation()

            # Results section
            if st.session_state.project_estimation_result:
                st.divider()
                st.subheader("📊 Estimation Results")

                result = st.session_state.project_estimation_result

                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                total_effort = result.get('total_effort', 0)
                total_confidence = result.get('total_confidence', 0)
                task_count = len(result.get('final_estimation_data', []))
                tasks_adjusted = result.get('tasks_adjusted', 0)

                with col1:
                    st.metric("Total Effort", f"{total_effort:.1f} mandays")
                with col2:
                    st.metric("Total Tasks", task_count)
                with col3:
                    st.metric("Avg Confidence", f"{total_confidence:.0%}")
                with col4:
                    st.metric("Tasks Adjusted", tasks_adjusted)

                # Detailed results table
                st.subheader("📋 Detailed Task Breakdown")
                estimation_data = result.get('final_estimation_data', [])

                if estimation_data:
                    # Convert to DataFrame for better display
                    df = pd.DataFrame(estimation_data)

                    # Select and rename columns for display - INCLUDING ROLE AND ROLE-SPECIFIC ESTIMATIONS
                    display_columns = ['id', 'category', 'role', 'parent_task', 'sub_task', 'description', 
                                      'estimation_backend_manday', 'estimation_frontend_manday', 
                                      'estimation_qa_manday', 'estimation_infra_manday',
                                      'estimation_manday', 'confidence_level']
                    
                    if all(col in df.columns for col in display_columns):
                        display_df = df[display_columns].copy()
                        display_df.columns = ['ID', 'Category', 'Role', 'Parent Task', 'Sub Task', 'Description',
                                             'Backend (days)', 'Frontend (days)', 'QA (days)', 'Infra (days)',
                                             'Total (days)', 'Confidence']
                        
                        # Round estimation columns
                        for col in ['Backend (days)', 'Frontend (days)', 'QA (days)', 'Infra (days)', 'Total (days)']:
                            display_df[col] = display_df[col].round(1)
                        
                        display_df['Confidence'] = (display_df['Confidence'] * 100).round(0).astype(int).astype(str) + '%'

                        st.dataframe(display_df, use_container_width=True, height=400)
                    else:
                        st.dataframe(df, use_container_width=True, height=400)
                
                # Add role summary metrics
                st.subheader("👥 Effort by Role")
                col1, col2, col3, col4 = st.columns(4)
                
                total_backend = df['estimation_backend_manday'].sum() if 'estimation_backend_manday' in df.columns else 0
                total_frontend = df['estimation_frontend_manday'].sum() if 'estimation_frontend_manday' in df.columns else 0
                total_qa = df['estimation_qa_manday'].sum() if 'estimation_qa_manday' in df.columns else 0
                total_infra = df['estimation_infra_manday'].sum() if 'estimation_infra_manday' in df.columns else 0
                
                with col1:
                    st.metric("Backend", f"{total_backend:.1f} days")
                with col2:
                    st.metric("Frontend", f"{total_frontend:.1f} days")
                with col3:
                    st.metric("QA", f"{total_qa:.1f} days")
                with col4:
                    st.metric("Infra", f"{total_infra:.1f} days")

                # Export and visualization section
                st.subheader("📁 Export & Visualization")
                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button("📥 Export to Excel", type="secondary"):
                        try:
                            excel_file = st.session_state.estimation_workflow.export_results(result)
                            if excel_file and os.path.exists(excel_file):
                                with open(excel_file, 'rb') as f:
                                    st.download_button(
                                        label="⬇️ Download Excel File",
                                        data=f.read(),
                                        file_name=os.path.basename(excel_file),
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                                st.success(f"✅ Excel file ready: {os.path.basename(excel_file)}")
                            else:
                                st.error("❌ Failed to create Excel file")
                        except Exception as e:
                            st.error(f"❌ Export error: {str(e)}")

                with col2:
                    if st.button("🎨 Show Mermaid Diagram", type="secondary"):
                        mermaid_diagram = st.session_state.estimation_workflow.get_mermaid_diagram(result)
                        if mermaid_diagram:
                            st.subheader("🔄 Project Workflow Diagram")
                            st.code(mermaid_diagram, language="mermaid")
                        else:
                            st.warning("⚠️ No diagram available")

                with col3:
                    if st.button("🗑️ Clear Results", type="secondary"):
                        st.session_state.project_estimation_result = None
                        st.rerun()

if __name__ == "__main__":
    main()
