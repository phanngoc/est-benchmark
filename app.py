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
from utils.architecture_diagram import ArchitectureDiagramGenerator
from utils.project_manager import get_project_manager

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
if 'selected_project_id' not in st.session_state:
    st.session_state.selected_project_id = None
if 'project_manager' not in st.session_state:
    st.session_state.project_manager = get_project_manager()

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
        if st.session_state.selected_project_id:
            logger.info(f"Estimation will be saved to project: {st.session_state.selected_project_id}")
        result = st.session_state.estimation_workflow.run_estimation(
            project_description,
            graphrag_insights=graphrag_insights,
            project_id=st.session_state.selected_project_id
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

        # Project Selector
        st.markdown("### 📁 Active Project")
        
        # Get all projects
        projects = st.session_state.project_manager.list_projects(status="active")
        
        if projects:
            project_options = {p['project_id']: f"{p['name']}" for p in projects}
            project_ids = list(project_options.keys())
            project_labels = list(project_options.values())
            
            # Add "No Project" option
            project_ids.insert(0, None)
            project_labels.insert(0, "-- No Project Selected --")
            
            # Find current index
            try:
                current_index = project_ids.index(st.session_state.selected_project_id) if st.session_state.selected_project_id else 0
            except ValueError:
                current_index = 0
            
            selected_label = st.selectbox(
                "Select Project",
                options=project_labels,
                index=current_index,
                key="project_selector"
            )
            
            # Update selected project ID
            selected_index = project_labels.index(selected_label)
            new_project_id = project_ids[selected_index]
            
            # Check if project changed
            if new_project_id != st.session_state.selected_project_id:
                st.session_state.selected_project_id = new_project_id
                # Reinitialize GraphRAG handler and workflow with new project
                if new_project_id:
                    st.session_state.graphrag_handler = GraphRAGHandler(
                        Config.WORKING_DIR,
                        project_id=new_project_id
                    )
                    st.session_state.estimation_workflow = EnhancedEstimationWorkflow(
                        project_id=new_project_id
                    )
                    logger.info(f"Switched to project: {new_project_id}")
                else:
                    st.session_state.graphrag_handler = GraphRAGHandler(Config.WORKING_DIR)
                    st.session_state.estimation_workflow = EnhancedEstimationWorkflow()
                    logger.info("Switched to no project")
                st.rerun()
            
            # Display selected project info
            if st.session_state.selected_project_id:
                project = st.session_state.project_manager.get_project(st.session_state.selected_project_id)
                if project:
                    st.info(f"📊 **{project['name']}**")
                    if project.get('description'):
                        st.caption(project['description'][:100] + "..." if len(project['description']) > 100 else project['description'])
                    
                    # Show project statistics
                    stats = st.session_state.project_manager.get_project_statistics(st.session_state.selected_project_id)
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📋 Estimations", stats['total_estimations'])
                    with col2:
                        st.metric("💼 Total Effort", f"{stats['total_effort']:.1f} MD")
        else:
            st.warning("⚠️ No active projects found. Create one in the Project Management tab.")
            st.session_state.selected_project_id = None

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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📁 Upload Files", "🔍 Query", "📋 Project Estimation", "📚 Estimation History", "📊 Master Data Management", "🏗️ System Architecture", "🗂️ Project Management"])
    
    with tab1:
        st.header("📁 Upload và Xử lý Tài liệu")
        
        # Show active project
        if st.session_state.selected_project_id:
            project = st.session_state.project_manager.get_project(st.session_state.selected_project_id)
            if project:
                st.info(f"📂 Active Project: **{project['name']}**")
        else:
            st.warning("⚠️ No project selected. Files will be uploaded to the global workspace.")
        
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
        
        # Show active project
        if st.session_state.selected_project_id:
            project = st.session_state.project_manager.get_project(st.session_state.selected_project_id)
            if project:
                st.info(f"📂 Active Project: **{project['name']}** - Queries are scoped to this project's data")
        else:
            st.info("🌐 Querying global workspace (no project selected)")

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
        
        # Show active project
        if st.session_state.selected_project_id:
            project = st.session_state.project_manager.get_project(st.session_state.selected_project_id)
            if project:
                st.info(f"📂 Active Project: **{project['name']}** - Estimations will be saved to this project")
        else:
            st.warning("⚠️ No project selected. Please select a project from the sidebar or create one in the Project Management tab.")

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
                    try:
                        excel_file, estimation_id = st.session_state.estimation_workflow.export_results(result)
                        if excel_file and os.path.exists(excel_file):
                            st.info(f"📋 Estimation ID: `{estimation_id}`")
                            with open(excel_file, 'rb') as f:
                                st.download_button(
                                    label="📥 Export to Excel",
                                    data=f.read(),
                                    file_name=os.path.basename(excel_file),
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    type="secondary"
                                )
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

    with tab4:
        st.header("📚 Estimation History")
        
        # Show active project
        if st.session_state.selected_project_id:
            project = st.session_state.project_manager.get_project(st.session_state.selected_project_id)
            if project:
                st.info(f"📂 Active Project: **{project['name']}** - Showing estimations for this project only")
        else:
            st.info("🌐 Showing all estimations (no project filter)")

        try:
            from utils.estimation_result_tracker import get_result_tracker

            # Get tracker
            tracker = get_result_tracker()

            # Get statistics (project-specific if selected)
            if st.session_state.selected_project_id:
                stats = st.session_state.project_manager.get_project_statistics(st.session_state.selected_project_id)
            else:
                stats = tracker.get_statistics()

            # Display summary statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Estimations", stats['total_estimations'])
            with col2:
                st.metric("Total Tasks", stats['total_tasks'])
            with col3:
                st.metric("Avg Effort", f"{stats['total_effort']:.1f} days" if 'total_effort' in stats else f"{stats['avg_effort']:.1f} days")
            with col4:
                st.metric("Avg Confidence", f"{stats['avg_confidence']:.0%}")

            st.divider()

            # List estimations with project filter
            if st.session_state.selected_project_id:
                estimations = tracker.search_estimations(
                    project_id=st.session_state.selected_project_id
                )
            else:
                estimations = tracker.list_all_estimations(limit=50)

            if estimations:
                st.subheader("📋 Recent Estimations")

                # Create DataFrame for display
                df_history = pd.DataFrame(estimations)

                # Select and rename columns for display
                display_columns = ['estimation_id', 'created_at', 'total_tasks', 'total_effort',
                                  'average_confidence', 'workflow_status']

                if all(col in df_history.columns for col in display_columns):
                    display_df = df_history[display_columns].copy()
                    display_df.columns = ['Estimation ID', 'Created At', 'Tasks',
                                         'Effort (days)', 'Confidence', 'Status']

                    # Format columns
                    display_df['Effort (days)'] = display_df['Effort (days)'].round(1)
                    display_df['Confidence'] = (display_df['Confidence'] * 100).round(0).astype(int).astype(str) + '%'

                    st.dataframe(display_df, use_container_width=True, height=300)
                else:
                    st.dataframe(df_history, use_container_width=True, height=300)

                st.divider()

                # Detail view with file download
                st.subheader("🔍 Estimation Details")

                # Select estimation
                selected_id = st.selectbox(
                    "Select Estimation ID to view details",
                    options=[e['estimation_id'] for e in estimations],
                    key="history_select"
                )

                if selected_id:
                    detail = tracker.get_estimation_by_id(selected_id)
                    tasks = tracker.get_estimation_tasks(selected_id)

                    if detail:
                        # Display run metadata
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown(f"**Estimation ID:** `{detail['estimation_id']}`")
                            st.markdown(f"**Created At:** {detail['created_at']}")
                            st.markdown(f"**Status:** {detail['workflow_status']}")
                            st.markdown(f"**Total Tasks:** {detail['total_tasks']}")

                        with col2:
                            st.markdown(f"**Total Effort:** {detail['total_effort']:.1f} mandays")
                            st.markdown(f"**Avg Confidence:** {detail['average_confidence']:.0%}")
                            st.markdown(f"**File Path:** `{detail['file_path']}`")

                        # Project description
                        if detail.get('project_description'):
                            with st.expander("📄 Project Description", expanded=False):
                                st.text(detail['project_description'])

                        # Download Excel file
                        if detail['file_path'] and os.path.exists(detail['file_path']):
                            with open(detail['file_path'], 'rb') as f:
                                st.download_button(
                                    label="📥 Download Excel File",
                                    data=f.read(),
                                    file_name=os.path.basename(detail['file_path']),
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key=f"download_{selected_id}"
                                )
                        else:
                            st.warning(f"⚠️ Excel file not found: {detail['file_path']}")

                        # Display tasks
                        if tasks:
                            st.subheader(f"📋 Tasks ({len(tasks)} total)")

                            df_tasks = pd.DataFrame(tasks)

                            # Select relevant columns for display
                            task_display_columns = ['id', 'category', 'role', 'parent_task', 'sub_task',
                                                   'estimation_manday', 'confidence_level', 'complexity']

                            existing_task_columns = [col for col in task_display_columns if col in df_tasks.columns]

                            if existing_task_columns:
                                st.dataframe(df_tasks[existing_task_columns], use_container_width=True, height=400)
                            else:
                                st.dataframe(df_tasks, use_container_width=True, height=400)
                        else:
                            st.info("No task details found for this estimation")
                    else:
                        st.warning(f"⚠️ Estimation {selected_id} not found in database")
            else:
                st.info("📭 No estimation history yet. Run your first project estimation to see it here!")

        except Exception as e:
            st.error(f"❌ Error loading estimation history: {str(e)}")
            logger.exception(f"Estimation history tab error: {e}")

    with tab5:
        st.header("📊 Master Data Management")
        
        # Master data is typically global, but we can show the project context
        st.info("ℹ️ Master data is shared across all projects for consistency")

        try:
            from utils.estimation_history_manager import get_history_manager

            history_manager = get_history_manager()

            # Section 1: CSV Import/Export (3-column layout for better UX)
            st.subheader("📥 CSV Operations")

            col1, col2, col3 = st.columns(3)

            # Column 1: Import CSV
            with col1:
                st.markdown("### 📥 Import CSV")
                uploaded_csv = st.file_uploader(
                    "Upload CSV File",
                    type=['csv'],
                    help="Upload CSV file with estimation master data",
                    key="master_data_csv_upload"
                )

                if uploaded_csv:
                    # Validate CSV
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                        tmp_file.write(uploaded_csv.getvalue())
                        tmp_path = tmp_file.name

                    is_valid, error_msg = history_manager.validate_csv_format(tmp_path)

                    if is_valid:
                        st.success(f"✅ Valid")

                        if st.button("📥 Import", type="primary", use_container_width=True):
                            with st.spinner("Importing..."):
                                try:
                                    count = history_manager.import_from_csv(tmp_path)
                                    st.success(f"✅ Imported {count} tasks!")
                                    os.unlink(tmp_path)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ {str(e)}")
                    else:
                        st.error(f"❌ {error_msg}")

                    # Clean up temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            # Column 2: Export CSV
            with col2:
                st.markdown("### 📤 Export CSV")
                st.caption("Export all master data to CSV file")

                export_filename = st.text_input(
                    "Filename",
                    value=f"master_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    key="export_filename",
                    label_visibility="collapsed"
                )

                if st.button("📤 Export", use_container_width=True):
                    try:
                        export_path = os.path.join(Config.RESULT_EST_DIR, export_filename)
                        os.makedirs(Config.RESULT_EST_DIR, exist_ok=True)

                        filepath = history_manager.export_to_csv(export_path)

                        # Download button
                        with open(filepath, 'rb') as f:
                            st.download_button(
                                label="📥 Download",
                                data=f.read(),
                                file_name=export_filename,
                                mime="text/csv",
                                use_container_width=True
                            )
                    except Exception as e:
                        st.error(f"❌ {str(e)}")

            # Column 3: CSV Template
            with col3:
                st.markdown("### 📋 CSV Template")
                st.caption("Download template with sample data")

                template_path = "./master_data_template.csv"
                if os.path.exists(template_path):
                    with open(template_path, 'rb') as f:
                        st.download_button(
                            label="📥 Download Template",
                            data=f.read(),
                            file_name="master_data_template.csv",
                            mime="text/csv",
                            help="CSV template with example estimation data",
                            use_container_width=True
                        )
                else:
                    st.warning("Template not found")

            st.divider()

            # Section 2: Task List with Filters
            st.subheader("📋 Task List")

            # Get statistics first
            stats = history_manager.get_statistics()

            # Filters
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                # Get unique categories
                all_tasks = history_manager.get_all_tasks_paginated(limit=1000)
                categories = sorted(list(set(task.get('_metadata', {}).get('category', 'Unknown') for task in all_tasks)))
                filter_category = st.selectbox(
                    "Category",
                    options=["All"] + categories,
                    key="filter_category"
                )

            with col2:
                filter_role = st.selectbox(
                    "Role",
                    options=["All", "Backend", "Frontend", "Testing", "Infra"],
                    key="filter_role"
                )

            with col3:
                filter_complexity = st.selectbox(
                    "Complexity",
                    options=["All", "Low", "Medium", "High"],
                    key="filter_complexity"
                )

            with col4:
                # Get unique project names
                projects = sorted(list(set(task.get('_metadata', {}).get('project_name', 'Unknown') for task in all_tasks)))
                filter_project = st.selectbox(
                    "Project",
                    options=["All"] + projects,
                    key="filter_project"
                )

            # Apply filters
            filter_kwargs = {}
            if filter_category != "All":
                filter_kwargs['category'] = filter_category
            if filter_role != "All":
                filter_kwargs['role'] = filter_role
            if filter_complexity != "All":
                filter_kwargs['complexity'] = filter_complexity
            if filter_project != "All":
                filter_kwargs['project_name'] = filter_project

            if filter_kwargs:
                filtered_tasks = history_manager.filter_by_criteria(**filter_kwargs)
            else:
                filtered_tasks = all_tasks

            # Display table with detailed estimation breakdown
            if filtered_tasks:
                st.markdown(f"**Found {len(filtered_tasks)} tasks**")

                # Prepare DataFrame with detailed estimation columns
                display_data = []
                for task in filtered_tasks:
                    metadata = task.get('_metadata', {})
                    display_data.append({
                        'ID': task.get('_id', '')[:8] + '...',
                        'Category': metadata.get('category', ''),
                        'Role': metadata.get('role', ''),
                        'Parent Task': task.get('parent_task', ''),
                        'Sub Task': task.get('sub_task', ''),
                        'Total': f"{metadata.get('estimation_manday', 0):.1f}",
                        'BE Impl': f"{metadata.get('backend_implement', 0):.1f}",
                        'BE Fix': f"{metadata.get('backend_fixbug', 0):.1f}",
                        'BE Test': f"{metadata.get('backend_unittest', 0):.1f}",
                        'FE Impl': f"{metadata.get('frontend_implement', 0):.1f}",
                        'FE Fix': f"{metadata.get('frontend_fixbug', 0):.1f}",
                        'FE Test': f"{metadata.get('frontend_unittest', 0):.1f}",
                        'Responsive': f"{metadata.get('responsive_implement', 0):.1f}",
                        'Testing': f"{metadata.get('testing_implement', 0):.1f}",
                        'Complexity': metadata.get('complexity', ''),
                        'Confidence': f"{metadata.get('confidence_level', 0):.0%}",
                        'Project': metadata.get('project_name', ''),
                        '_task_id': task.get('_id', '')
                    })

                df_display = pd.DataFrame(display_data)

                # Display with horizontal scroll for detailed view
                st.dataframe(
                    df_display.drop('_task_id', axis=1),
                    use_container_width=True,
                    height=400
                )

                # Action buttons
                st.markdown("### 🔧 Actions")
                selected_task_id = st.selectbox(
                    "Select task for action",
                    options=[t['_id'] for t in filtered_tasks],
                    format_func=lambda x: f"{x[:8]}... - {next((t.get('sub_task', 'Unknown') for t in filtered_tasks if t.get('_id') == x), 'Unknown')}",
                    key="selected_task_action"
                )

                col_edit, col_delete = st.columns(2)

                with col_edit:
                    if st.button("✏️ Edit Task", use_container_width=True):
                        st.session_state['editing_task_id'] = selected_task_id
                        st.rerun()

                with col_delete:
                    if st.button("🗑️ Delete Task", use_container_width=True, type="secondary"):
                        if history_manager.delete_task(selected_task_id):
                            st.success(f"✅ Deleted task: {selected_task_id}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete task")
            else:
                st.info("📭 No tasks found. Import CSV or add tasks manually.")

            st.divider()

            # Section 3: Add/Edit Task Form
            if st.session_state.get('editing_task_id'):
                st.subheader("✏️ Edit Task")
                task_to_edit = history_manager.get_task_by_id(st.session_state['editing_task_id'])

                if task_to_edit:
                    form_data = {
                        'id': st.session_state['editing_task_id'],
                        'category': task_to_edit.get('category', ''),
                        'role': task_to_edit.get('_metadata', {}).get('role', 'Backend'),
                        'parent_task': task_to_edit.get('parent_task', ''),
                        'sub_task': task_to_edit.get('sub_task', ''),
                        'description': task_to_edit.get('description', ''),
                        'complexity': task_to_edit.get('_metadata', {}).get('complexity', 'Medium'),
                        'priority': task_to_edit.get('_metadata', {}).get('priority', 'Medium'),
                        'estimation_manday': task_to_edit.get('_metadata', {}).get('estimation_manday', 0.0),
                        'backend_implement': task_to_edit.get('_metadata', {}).get('backend_implement', 0.0),
                        'backend_fixbug': task_to_edit.get('_metadata', {}).get('backend_fixbug', 0.0),
                        'backend_unittest': task_to_edit.get('_metadata', {}).get('backend_unittest', 0.0),
                        'frontend_implement': task_to_edit.get('_metadata', {}).get('frontend_implement', 0.0),
                        'frontend_fixbug': task_to_edit.get('_metadata', {}).get('frontend_fixbug', 0.0),
                        'frontend_unittest': task_to_edit.get('_metadata', {}).get('frontend_unittest', 0.0),
                        'responsive_implement': task_to_edit.get('_metadata', {}).get('responsive_implement', 0.0),
                        'testing_implement': task_to_edit.get('_metadata', {}).get('testing_implement', 0.0),
                        'confidence_level': task_to_edit.get('_metadata', {}).get('confidence_level', 0.8),
                        'validated': task_to_edit.get('_metadata', {}).get('validated', False),
                        'project_name': task_to_edit.get('_metadata', {}).get('project_name', '')
                    }
                else:
                    st.error("Task not found")
                    st.session_state.pop('editing_task_id')
                    st.rerun()
            else:
                st.subheader("➕ Add New Task")
                form_data = {
                    'id': None,
                    'category': '',
                    'role': 'Backend',
                    'parent_task': '',
                    'sub_task': '',
                    'description': '',
                    'complexity': 'Medium',
                    'priority': 'Medium',
                    'estimation_manday': 0.0,
                    'backend_implement': 0.0,
                    'backend_fixbug': 0.0,
                    'backend_unittest': 0.0,
                    'frontend_implement': 0.0,
                    'frontend_fixbug': 0.0,
                    'frontend_unittest': 0.0,
                    'responsive_implement': 0.0,
                    'testing_implement': 0.0,
                    'confidence_level': 0.8,
                    'validated': False,
                    'project_name': ''
                }

            with st.form("task_form"):
                col1, col2 = st.columns(2)

                with col1:
                    category = st.text_input("Category *", value=form_data['category'])

                    # Handle role with safe index lookup (support both QA and Testing)
                    role_options = ["Backend", "Frontend", "Testing", "Infra"]
                    current_role = form_data['role']
                    # Convert QA to Testing for compatibility
                    if current_role == 'QA':
                        current_role = 'Testing'
                    try:
                        role_index = role_options.index(current_role)
                    except ValueError:
                        role_index = 0  # Default to Backend if role not found

                    role = st.selectbox("Role *", role_options, index=role_index)
                    parent_task = st.text_input("Parent Task", value=form_data['parent_task'])
                    sub_task = st.text_input("Sub Task *", value=form_data['sub_task'])
                    description = st.text_area("Description *", value=form_data['description'], height=100)

                with col2:
                    complexity = st.selectbox("Complexity", ["Low", "Medium", "High"],
                                            index=["Low", "Medium", "High"].index(form_data['complexity']))
                    priority = st.selectbox("Priority", ["Low", "Medium", "High"],
                                           index=["Low", "Medium", "High"].index(form_data['priority']))
                    project_name = st.text_input("Project Name", value=form_data['project_name'])
                    confidence_level = st.slider("Confidence Level", 0.0, 1.0, form_data['confidence_level'], 0.05)
                    validated = st.checkbox("Validated", value=form_data['validated'])

                st.markdown("### Effort Breakdown (mandays)")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**Backend**")
                    backend_implement = st.number_input("Implement", value=form_data['backend_implement'],
                                                       min_value=0.0, step=0.1, format="%.1f", key="backend_impl")
                    backend_fixbug = st.number_input("Fix Bug", value=form_data['backend_fixbug'],
                                                    min_value=0.0, step=0.1, format="%.1f", key="backend_fix")
                    backend_unittest = st.number_input("Unit Test", value=form_data['backend_unittest'],
                                                      min_value=0.0, step=0.1, format="%.1f", key="backend_test")

                with col2:
                    st.markdown("**Frontend**")
                    frontend_implement = st.number_input("Implement", value=form_data['frontend_implement'],
                                                        min_value=0.0, step=0.1, format="%.1f", key="frontend_impl")
                    frontend_fixbug = st.number_input("Fix Bug", value=form_data['frontend_fixbug'],
                                                     min_value=0.0, step=0.1, format="%.1f", key="frontend_fix")
                    frontend_unittest = st.number_input("Unit Test", value=form_data['frontend_unittest'],
                                                       min_value=0.0, step=0.1, format="%.1f", key="frontend_test")

                with col3:
                    st.markdown("**Other**")
                    responsive_implement = st.number_input("Responsive", value=form_data['responsive_implement'],
                                                          min_value=0.0, step=0.1, format="%.1f", key="responsive")
                    testing_implement = st.number_input("Testing", value=form_data['testing_implement'],
                                                       min_value=0.0, step=0.1, format="%.1f", key="testing")

                # Calculate total
                total_estimation = (backend_implement + backend_fixbug + backend_unittest +
                                  frontend_implement + frontend_fixbug + frontend_unittest +
                                  responsive_implement + testing_implement)

                st.markdown(f"**Total Estimation:** {total_estimation:.1f} mandays")

                # Form buttons
                col_save, col_cancel = st.columns([1, 1])

                with col_save:
                    submitted = st.form_submit_button("💾 Save Task", type="primary", use_container_width=True)

                with col_cancel:
                    cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

            # Handle form submission OUTSIDE the form block
            if submitted:
                # Validate required fields
                if not category or not sub_task or not description:
                    st.error("❌ Please fill in all required fields (Category, Sub Task, Description)")
                else:
                    # Prepare task data
                    task_data = {
                        'category': category,
                        'role': role,
                        'parent_task': parent_task,
                        'sub_task': sub_task,
                        'description': description,
                        'complexity': complexity,
                        'priority': priority,
                        'estimation_manday': total_estimation,
                        'backend_implement': backend_implement,
                        'backend_fixbug': backend_fixbug,
                        'backend_unittest': backend_unittest,
                        'frontend_implement': frontend_implement,
                        'frontend_fixbug': frontend_fixbug,
                        'frontend_unittest': frontend_unittest,
                        'responsive_implement': responsive_implement,
                        'testing_implement': testing_implement,
                        'confidence_level': confidence_level,
                        'validated': validated,
                        'project_name': project_name or 'manual_entry'
                    }

                    try:
                        if form_data['id']:
                            # Update existing task
                            success = history_manager.update_task(form_data['id'], task_data)
                            if success:
                                st.success(f"✅ Task updated successfully!")
                                st.session_state.pop('editing_task_id', None)
                                st.rerun()
                            else:
                                st.error("❌ Failed to update task")
                        else:
                            # Add new task
                            task_id = history_manager.save_estimation(task_data, project_name=project_name or 'manual_entry')
                            st.success(f"✅ Task added successfully! ID: {task_id}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error saving task: {str(e)}")

            if cancel:
                st.session_state.pop('editing_task_id', None)
                st.rerun()

            st.divider()

            # Section 4: Statistics Dashboard
            st.subheader("📊 Statistics")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Tasks", stats['total_tasks'])

            with col2:
                st.metric("Avg Estimation", f"{stats['avg_estimation']:.1f} days")

            with col3:
                st.metric("Avg Confidence", f"{stats['avg_confidence']:.0%}")

            with col4:
                st.metric("Categories", len(stats.get('by_category', {})))

            # Charts
            col1, col2, col3 = st.columns(3)

            with col1:
                if stats.get('by_role'):
                    st.markdown("**Distribution by Role**")
                    role_df = pd.DataFrame(list(stats['by_role'].items()), columns=['Role', 'Count'])
                    st.bar_chart(role_df.set_index('Role'))

            with col2:
                if stats.get('by_category'):
                    st.markdown("**Distribution by Category**")
                    # Limit to top 10 categories
                    cat_items = sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True)[:10]
                    cat_df = pd.DataFrame(cat_items, columns=['Category', 'Count'])
                    st.bar_chart(cat_df.set_index('Category'))

            with col3:
                if stats.get('by_complexity'):
                    st.markdown("**Distribution by Complexity**")
                    comp_df = pd.DataFrame(list(stats['by_complexity'].items()), columns=['Complexity', 'Count'])
                    st.bar_chart(comp_df.set_index('Complexity'))

        except Exception as e:
            st.error(f"❌ Error in Master Data Management: {str(e)}")
            logger.exception(f"Master Data Management error: {e}")

    with tab6:
        st.header("🏗️ System Architecture Diagram")
        
        # Show active project
        if st.session_state.selected_project_id:
            project = st.session_state.project_manager.get_project(st.session_state.selected_project_id)
            if project:
                st.info(f"📂 Active Project: **{project['name']}**")

        try:
            import sqlite3
            from utils.estimation_result_tracker import get_result_tracker

            tracker = get_result_tracker()

            # Get latest estimation (filtered by project if selected)
            if st.session_state.selected_project_id:
                estimations = tracker.search_estimations(
                    project_id=st.session_state.selected_project_id
                )
                estimations = estimations[:1] if estimations else []
            else:
                estimations = tracker.list_all_estimations(limit=1)

            if not estimations:
                st.info("📭 Chưa có estimation nào. Vui lòng chạy Project Estimation trước.")
            else:
                latest_estimation = estimations[0]
                estimation_id = latest_estimation['estimation_id']
                project_description = latest_estimation.get('project_description', '')

                st.subheader("📋 Project Information")

                # Display estimation metadata
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Estimation ID", estimation_id[:8] + "...")
                with col2:
                    st.metric("Created At", latest_estimation['created_at'])
                with col3:
                    st.metric("Total Effort", f"{latest_estimation['total_effort']:.1f} days")

                # Display project description
                with st.expander("📄 Project Description", expanded=False):
                    st.text_area(
                        "Full Description",
                        value=project_description,
                        height=200,
                        disabled=True,
                        key="arch_project_desc"
                    )

                st.divider()

                # Architecture diagram generation section
                st.subheader("🎨 Generate Architecture Diagram")

                st.markdown("""
                **Chức năng này sẽ:**
                - 🧠 Phân tích project description bằng AI
                - 🔍 Tự động nhận diện các components chính (Backend, Frontend, Database, Mobile, Third-party)
                - 🎨 Tạo architecture diagram rõ ràng, chuyên nghiệp
                - 📥 Export ra file PNG để sử dụng trong proposal
                """)

                # Generate button
                if st.button("🎨 Generate Architecture Diagram", type="primary", key="generate_arch_diagram"):
                    with st.spinner("🔄 Đang phân tích và tạo diagram..."):
                        try:
                            # Initialize diagram generator
                            diagram_gen = ArchitectureDiagramGenerator()

                            # Generate diagram with fallback for config
                            output_dir = getattr(Config, 'ARCHITECTURE_DIAGRAMS_DIR', './architecture_diagrams')
                            diagram_path = diagram_gen.generate_diagram(
                                project_description,
                                output_dir=output_dir
                            )

                            if diagram_path and os.path.exists(diagram_path):
                                st.success("✅ Architecture diagram đã được tạo thành công!")
                                st.session_state['arch_diagram_path'] = diagram_path

                                # Extract components info for display
                                components, connections = diagram_gen.extract_components(project_description)
                                diagram_info = diagram_gen.get_diagram_info(components, connections)
                                st.session_state['arch_diagram_info'] = diagram_info

                                st.rerun()
                            else:
                                st.error("❌ Không thể tạo diagram. Vui lòng kiểm tra logs.")
                                logger.error("Diagram generation returned None or file not found")

                        except Exception as e:
                            st.error(f"❌ Lỗi khi tạo diagram: {str(e)}")
                            logger.exception(f"Architecture diagram generation error: {e}")

                # Display generated diagram if exists
                if st.session_state.get('arch_diagram_path'):
                    diagram_path = st.session_state['arch_diagram_path']

                    if os.path.exists(diagram_path):
                        st.divider()
                        st.subheader("📊 Generated Architecture Diagram")

                        # Display diagram image
                        st.image(diagram_path, caption="System Architecture Diagram", use_container_width=True)

                        # Display component info
                        if st.session_state.get('arch_diagram_info'):
                            info = st.session_state['arch_diagram_info']

                            st.subheader("🔍 Architecture Summary")

                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Total Components", info['total_components'])
                            with col2:
                                st.metric("Total Connections", info['total_connections'])

                            # Component types breakdown
                            if info.get('component_types'):
                                st.markdown("**Component Types:**")
                                types_df = pd.DataFrame(
                                    list(info['component_types'].items()),
                                    columns=['Type', 'Count']
                                )
                                st.dataframe(types_df, use_container_width=True, hide_index=True)

                            # Detailed component list
                            with st.expander("📋 Detailed Component List", expanded=False):
                                components_df = pd.DataFrame(info['components'])
                                st.dataframe(components_df, use_container_width=True, hide_index=True)

                        st.divider()

                        # Export section
                        st.subheader("📥 Export Diagram")

                        col1, col2 = st.columns(2)

                        with col1:
                            # Download PNG
                            with open(diagram_path, 'rb') as f:
                                st.download_button(
                                    label="📥 Download PNG",
                                    data=f.read(),
                                    file_name=f"architecture_diagram_{estimation_id[:8]}.png",
                                    mime="image/png",
                                    type="primary",
                                    use_container_width=True
                                )

                        with col2:
                            # Regenerate button
                            if st.button("🔄 Regenerate Diagram", type="secondary", use_container_width=True):
                                st.session_state.pop('arch_diagram_path', None)
                                st.session_state.pop('arch_diagram_info', None)
                                st.rerun()

                    else:
                        st.warning("⚠️ Diagram file không tồn tại. Vui lòng generate lại.")
                        st.session_state.pop('arch_diagram_path', None)

        except Exception as e:
            st.error(f"❌ Error in System Architecture tab: {str(e)}")
            logger.exception(f"System Architecture tab error: {e}")

    with tab7:
        st.header("🗂️ Project Management")
        
        try:
            # Project Management UI
            st.markdown("""
            Manage your estimation projects here. Each project can have multiple estimation runs and tasks.
            """)
            
            # Create/Edit Project Section
            st.subheader("➕ Create New Project")
            
            with st.form("create_project_form"):
                new_project_name = st.text_input(
                    "Project Name *",
                    placeholder="e.g., E-commerce Platform",
                    help="Enter a descriptive name for your project"
                )
                new_project_description = st.text_area(
                    "Project Description",
                    placeholder="Brief description of the project...",
                    height=100,
                    help="Optional detailed description"
                )
                new_project_status = st.selectbox(
                    "Status",
                    options=["active", "on-hold", "completed", "archived"],
                    index=0
                )
                
                submitted = st.form_submit_button("✅ Create Project", type="primary")
                
                if submitted:
                    if not new_project_name:
                        st.error("❌ Project name is required!")
                    else:
                        try:
                            project_id = st.session_state.project_manager.create_project(
                                name=new_project_name,
                                description=new_project_description,
                                status=new_project_status
                            )
                            st.success(f"✅ Project created successfully! ID: {project_id}")
                            logger.info(f"Created new project: {project_id} - {new_project_name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error creating project: {str(e)}")
                            logger.error(f"Failed to create project: {e}")
            
            st.divider()
            
            # List and Manage Existing Projects
            st.subheader("📋 Existing Projects")
            
            # Filter options
            col1, col2 = st.columns([3, 1])
            with col1:
                search_keyword = st.text_input(
                    "🔍 Search Projects",
                    placeholder="Search by name or description...",
                    key="project_search"
                )
            with col2:
                filter_status = st.selectbox(
                    "Filter by Status",
                    options=["all", "active", "on-hold", "completed", "archived"],
                    index=0,
                    key="project_filter_status"
                )
            
            # Fetch projects based on filters
            if search_keyword:
                projects = st.session_state.project_manager.search_projects(
                    keyword=search_keyword,
                    status=filter_status if filter_status != "all" else None
                )
            else:
                projects = st.session_state.project_manager.list_projects(
                    status=filter_status if filter_status != "all" else None
                )
            
            if not projects:
                st.info("ℹ️ No projects found. Create your first project above!")
            else:
                st.markdown(f"**Found {len(projects)} project(s)**")
                
                # Display projects in expandable cards
                for project in projects:
                    with st.expander(
                        f"**{project['name']}** ({project['status']}) - {project['project_id'][:12]}...",
                        expanded=False
                    ):
                        # Project details
                        st.markdown(f"**Project ID:** `{project['project_id']}`")
                        st.markdown(f"**Status:** `{project['status']}`")
                        st.markdown(f"**Created:** {project['created_at']}")
                        st.markdown(f"**Updated:** {project['updated_at']}")
                        
                        if project.get('description'):
                            st.markdown(f"**Description:**")
                            st.text_area(
                                "Description",
                                value=project['description'],
                                height=100,
                                disabled=True,
                                key=f"desc_{project['project_id']}",
                                label_visibility="collapsed"
                            )
                        
                        # Get project statistics
                        stats = st.session_state.project_manager.get_project_statistics(project['project_id'])
                        
                        st.markdown("**📊 Project Statistics:**")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Estimations", stats['total_estimations'])
                        with col2:
                            st.metric("Tasks", stats['total_tasks'])
                        with col3:
                            st.metric("Total Effort", f"{stats['total_effort']:.1f} MD")
                        with col4:
                            st.metric("Avg Confidence", f"{stats['avg_confidence']:.0%}")
                        
                        st.divider()
                        
                        # Action buttons
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            # Edit button
                            if st.button(
                                "✏️ Edit",
                                key=f"edit_{project['project_id']}",
                                use_container_width=True
                            ):
                                st.session_state[f"editing_{project['project_id']}"] = True
                                st.rerun()
                        
                        with col2:
                            # Set as active project button
                            if st.button(
                                "📌 Set Active",
                                key=f"activate_{project['project_id']}",
                                use_container_width=True,
                                disabled=(st.session_state.selected_project_id == project['project_id'])
                            ):
                                st.session_state.selected_project_id = project['project_id']
                                st.session_state.graphrag_handler = GraphRAGHandler(
                                    Config.WORKING_DIR,
                                    project_id=project['project_id']
                                )
                                st.session_state.estimation_workflow = EnhancedEstimationWorkflow(
                                    project_id=project['project_id']
                                )
                                st.success(f"✅ Activated project: {project['name']}")
                                logger.info(f"Activated project: {project['project_id']}")
                                st.rerun()
                        
                        with col3:
                            # Delete button
                            if st.button(
                                "🗑️ Delete",
                                key=f"delete_{project['project_id']}",
                                use_container_width=True,
                                type="secondary"
                            ):
                                st.session_state[f"confirm_delete_{project['project_id']}"] = True
                                st.rerun()
                        
                        # Edit form (shown when edit is clicked)
                        if st.session_state.get(f"editing_{project['project_id']}", False):
                            st.markdown("---")
                            st.markdown("**✏️ Edit Project:**")
                            
                            with st.form(f"edit_form_{project['project_id']}"):
                                edit_name = st.text_input(
                                    "Project Name",
                                    value=project['name'],
                                    key=f"edit_name_{project['project_id']}"
                                )
                                edit_description = st.text_area(
                                    "Description",
                                    value=project.get('description', ''),
                                    height=100,
                                    key=f"edit_desc_{project['project_id']}"
                                )
                                edit_status = st.selectbox(
                                    "Status",
                                    options=["active", "on-hold", "completed", "archived"],
                                    index=["active", "on-hold", "completed", "archived"].index(project['status']),
                                    key=f"edit_status_{project['project_id']}"
                                )
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                                        try:
                                            success = st.session_state.project_manager.update_project(
                                                project_id=project['project_id'],
                                                name=edit_name,
                                                description=edit_description,
                                                status=edit_status
                                            )
                                            if success:
                                                st.success("✅ Project updated successfully!")
                                                logger.info(f"Updated project: {project['project_id']}")
                                                st.session_state.pop(f"editing_{project['project_id']}", None)
                                                st.rerun()
                                            else:
                                                st.error("❌ Failed to update project")
                                        except Exception as e:
                                            st.error(f"❌ Error: {str(e)}")
                                            logger.error(f"Failed to update project: {e}")
                                
                                with col2:
                                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                                        st.session_state.pop(f"editing_{project['project_id']}", None)
                                        st.rerun()
                        
                        # Delete confirmation (shown when delete is clicked)
                        if st.session_state.get(f"confirm_delete_{project['project_id']}", False):
                            st.markdown("---")
                            st.warning(f"⚠️ **Confirm Deletion**")
                            st.markdown(f"Are you sure you want to delete **{project['name']}**?")
                            
                            if stats['total_estimations'] > 0:
                                st.error(
                                    f"⚠️ This project has **{stats['total_estimations']} estimation(s)** "
                                    f"and **{stats['total_tasks']} task(s)**. All associated data will be deleted!"
                                )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(
                                    "✅ Yes, Delete",
                                    key=f"confirm_yes_{project['project_id']}",
                                    type="primary",
                                    use_container_width=True
                                ):
                                    try:
                                        # Delete with cascade
                                        success = st.session_state.project_manager.delete_project(
                                            project_id=project['project_id'],
                                            cascade=True
                                        )
                                        if success:
                                            st.success(f"✅ Project '{project['name']}' deleted successfully!")
                                            logger.info(f"Deleted project: {project['project_id']}")
                                            
                                            # Clear selection if deleted project was active
                                            if st.session_state.selected_project_id == project['project_id']:
                                                st.session_state.selected_project_id = None
                                                st.session_state.graphrag_handler = GraphRAGHandler(Config.WORKING_DIR)
                                                st.session_state.estimation_workflow = EnhancedEstimationWorkflow()
                                            
                                            st.session_state.pop(f"confirm_delete_{project['project_id']}", None)
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to delete project")
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
                                        logger.error(f"Failed to delete project: {e}")
                            
                            with col2:
                                if st.button(
                                    "❌ Cancel",
                                    key=f"confirm_no_{project['project_id']}",
                                    use_container_width=True
                                ):
                                    st.session_state.pop(f"confirm_delete_{project['project_id']}", None)
                                    st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error in Project Management tab: {str(e)}")
            logger.exception(f"Project Management tab error: {e}")

if __name__ == "__main__":
    main()
