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
from enhanced_estimation_workflow import EnhancedEstimationWorkflow

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
if 'estimation_workflow' not in st.session_state:
    st.session_state.estimation_workflow = EnhancedEstimationWorkflow()
if 'project_estimation_result' not in st.session_state:
    st.session_state.project_estimation_result = None
if 'estimation_in_progress' not in st.session_state:
    st.session_state.estimation_in_progress = False

def auto_analyze_project_scope(graphrag_handler) -> str:
    """
    Auto-generate comprehensive project description from uploaded documents
    """
    if not graphrag_handler or not graphrag_handler.is_initialized:
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
        except Exception as e:
            st.warning(f"Could not analyze: {query[:50]}... - {str(e)}")
            continue

    if not project_insights:
        return ""

    # Combine insights into comprehensive project description
    combined_description = f"""
Develop a project with the following requirements extracted from documents:

{chr(10).join([f"- {insight}" for insight in project_insights])}

The project needs to be broken down into specific tasks with effort estimation suitable for middle developer (3 years experience).
"""

    return combined_description.strip()

def run_project_estimation():
    """
    Main function to run project estimation with Streamlit integration
    """
    if st.session_state.estimation_in_progress:
        st.warning("🔄 Estimation is running. Please wait...")
        return

    if not st.session_state.graphrag_handler.is_initialized:
        st.error("❌ GraphRAG is not initialized. Please initialize GraphRAG first.")
        return

    if not st.session_state.processed_files:
        st.error("❌ No documents have been processed. Please upload and process documents first.")
        return

    try:
        st.session_state.estimation_in_progress = True

        # Step 1: Auto analyze project scope
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("🔍 Analyzing documents to understand project scope...")
        progress_bar.progress(10)

        project_description = auto_analyze_project_scope(st.session_state.graphrag_handler)

        if not project_description:
            st.error("❌ Cannot analyze project from documents. Please check the documents again.")
            return

        # Step 2: Pre-fetch GraphRAG insights to avoid serialization issues
        status_text.text("🔍 Pre-fetching GraphRAG insights...")
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
        status_text.text("🚀 Running estimation workflow...")
        progress_bar.progress(50)

        result = st.session_state.estimation_workflow.run_estimation(
            project_description,
            graphrag_insights=graphrag_insights
        )

        if result and result.get('workflow_status') == 'completed':
            status_text.text("✅ Estimation completed!")
            progress_bar.progress(100)

            st.session_state.project_estimation_result = result
            st.success("🎉 Project estimation completed successfully!")

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
            st.error("❌ Estimation workflow failed. Please try again.")

    except Exception as e:
        st.error(f"❌ Error running estimation: {str(e)}")
    finally:
        st.session_state.estimation_in_progress = False

def main():
    """Main application function"""
    
    # Header
    st.title("🧠 " + Config.APP_TITLE)
    st.markdown(f"**{Config.APP_DESCRIPTION}**")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key input
        api_key = st.text_input(
            "OpenAI API Key",
            value=Config.OPENAI_API_KEY,
            type="password",
            help="Enter your API key from OpenAI"
        )
        
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # Domain configuration
        st.subheader("📝 Domain Configuration")
        domain = st.text_area(
            "Domain description:",
            value=Config.DEFAULT_DOMAIN,
            height=100,
            help="Describe the field and objectives for document analysis"
        )
        
        # Entity types
        st.subheader("🏷️ Entity Types")
        entity_types_input = st.text_area(
            "Entity types (one per line):",
            value="\n".join(Config.DEFAULT_ENTITY_TYPES),
            height=150,
            help="Entity types that you want GraphRAG to recognize"
        )
        entity_types = [t.strip() for t in entity_types_input.split('\n') if t.strip()]
        
        # Example queries
        st.subheader("❓ Example Queries")
        example_queries_input = st.text_area(
            "Sample queries (one per line):",
            value="\n".join(Config.DEFAULT_EXAMPLE_QUERIES),
            height=150,
            help="Sample queries to help GraphRAG understand how to respond"
        )
        example_queries = [q.strip() for q in example_queries_input.split('\n') if q.strip()]
        
        # Initialize GraphRAG button
        if st.button("🚀 Initialize GraphRAG", type="primary"):
            with st.spinner("Initializing GraphRAG..."):
                success = st.session_state.graphrag_handler.initialize(
                    domain=domain,
                    entity_types=entity_types,
                    example_queries=example_queries
                )
                if success:
                    st.success("✅ GraphRAG initialized successfully!")
                else:
                    st.error("❌ Error initializing GraphRAG")
    
    # Main content area
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📁 Upload Files", "🔍 Query", "📋 Project Estimation", "📊 Visualization", "ℹ️ Info"])
    
    with tab1:
        st.header("📁 Upload and Process Documents")
        
        # File upload
        uploaded_files = st.file_uploader(
            "Select documents to analyze",
            type=['txt', 'pdf', 'docx', 'md'],
            accept_multiple_files=True,
            help="Supported: TXT, PDF, DOCX, MD (max 200MB per file)"
        )
        
        if uploaded_files:
            # Process files
            if st.button("🔄 Process Files", type="primary"):
                with st.spinner("Processing files..."):
                    processed_files = FileProcessor.process_uploaded_files(uploaded_files)
                    st.session_state.processed_files = processed_files
                    
                    if processed_files:
                        st.success(f"✅ Successfully processed {len(processed_files)} files!")
                        
                        # Show file info
                        st.subheader("📋 File Information")
                        for file_info in processed_files:
                            with st.expander(f"📄 {file_info['name']} ({file_info['size_mb']:.1f}MB)"):
                                preview = FileProcessor.get_file_preview(file_info['content'])
                                st.text(preview)
        
        # Show processed files
        if st.session_state.processed_files:
            st.subheader("📚 Processed Files")
            
            # File statistics
            total_size = sum(f['size_mb'] for f in st.session_state.processed_files)
            file_types = {}
            for f in st.session_state.processed_files:
                file_type = f['type']
                file_types[file_type] = file_types.get(file_type, 0) + 1
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Files", len(st.session_state.processed_files))
            with col2:
                st.metric("Total Size", f"{total_size:.1f} MB")
            with col3:
                st.metric("File Types", len(file_types))
            
            # Insert into GraphRAG
            if st.session_state.graphrag_handler.is_initialized:
                if st.button("📥 Add to GraphRAG", type="primary"):
                    with st.spinner("Adding documents to GraphRAG..."):
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
                            st.success("✅ Successfully added documents to GraphRAG!")
                        else:
                            st.error("❌ Error adding documents to GraphRAG")
            else:
                st.warning("⚠️ Please initialize GraphRAG before adding documents")
    
    with tab2:
        st.header("🔍 Query GraphRAG")
        
        if not st.session_state.graphrag_handler.is_initialized:
            st.warning("⚠️ Please initialize GraphRAG before querying")
        else:
            # Query input
            query = st.text_input(
                "Enter your question:",
                placeholder="Example: What topics does this document discuss?",
                help="Enter a question to search for information from processed documents"
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                with_references = st.checkbox("Show references", value=True)
            
            with col2:
                if st.button("🔍 Search", type="primary"):
                    if query:
                        with st.spinner("Searching..."):
                            result = st.session_state.graphrag_handler.query(
                                query, 
                                with_references=with_references
                            )
                            
                            if result:
                                # Add to query history
                                st.session_state.query_history.append(result)
                                
                                # Display result
                                st.subheader("💡 Result")
                                st.write(result['response'])
                                
                                # Display references if available
                                if with_references and result.get('references'):
                                    references_html = GraphVisualization.create_references_display(
                                        result['references']
                                    )
                                    st.markdown(references_html, unsafe_allow_html=True)
                            else:
                                st.error("❌ Unable to perform query")
                    else:
                        st.warning("⚠️ Please enter a question")
            
            # Query history
            if st.session_state.query_history:
                st.subheader("📜 Query History")
                
                # Create query history table
                history_df = GraphVisualization.create_query_results_table(
                    st.session_state.query_history
                )
                st.dataframe(history_df, use_container_width=True)
                
                # Clear history button
                if st.button("🗑️ Clear History"):
                    st.session_state.query_history = []
                    st.rerun()

    with tab3:
        st.header("📋 Project Estimation")

        # Prerequisites check section
        st.subheader("🔍 Prerequisites Check")
        col1, col2, col3 = st.columns(3)

        with col1:
            graphrag_status = "✅ Initialized" if st.session_state.graphrag_handler.is_initialized else "❌ Not Initialized"
            st.metric("GraphRAG Status", graphrag_status)

        with col2:
            files_count = len(st.session_state.processed_files)
            files_status = f"✅ {files_count} files" if files_count > 0 else "❌ No files"
            st.metric("Documents", files_status)

        with col3:
            ready_status = "✅ Ready" if (st.session_state.graphrag_handler.is_initialized and files_count > 0) else "❌ Not Ready"
            st.metric("Estimation Ready", ready_status)

        st.divider()

        # Main estimation section
        if not st.session_state.graphrag_handler.is_initialized:
            st.warning("⚠️ Please initialize GraphRAG before performing estimation.")
            st.info("💡 Go to 'Upload Files' tab to initialize GraphRAG and upload documents.")
        elif not st.session_state.processed_files:
            st.warning("⚠️ Please upload and process documents before performing estimation.")
            st.info("💡 Go to 'Upload Files' tab to upload project documents.")
        else:
            # One-click estimation button
            st.subheader("🚀 Auto Project Analysis & Estimation")
            st.markdown("""
            **This feature will:**
            - 🔍 Automatically analyze all uploaded documents
            - 🧠 Use GraphRAG to understand project scope and requirements
            - 📋 Break down project into specific tasks
            - ⏱️ Estimate effort for each task (target: middle developer 3 years experience)
            - 📊 Generate complete estimation report with Excel export
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

                    # Select and rename columns for display
                    display_columns = ['id', 'category', 'parent_task', 'sub_task', 'description', 'estimation_manday', 'confidence_level']
                    if all(col in df.columns for col in display_columns):
                        display_df = df[display_columns].copy()
                        display_df.columns = ['ID', 'Category', 'Parent Task', 'Sub Task', 'Description', 'Effort (mandays)', 'Confidence']
                        display_df['Effort (mandays)'] = display_df['Effort (mandays)'].round(1)
                        display_df['Confidence'] = (display_df['Confidence'] * 100).round(0).astype(int).astype(str) + '%'

                        st.dataframe(display_df, use_container_width=True, height=400)
                    else:
                        st.dataframe(df, use_container_width=True, height=400)

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

    with tab4:
        st.header("📊 Visualization")
        
        if not st.session_state.graphrag_handler.is_initialized:
            st.warning("⚠️ Please initialize GraphRAG and add documents before viewing visualization")
        else:
            # Get graph info
            graph_info = st.session_state.graphrag_handler.get_graph_info()
            
            if graph_info:
                st.subheader("📈 Graph Statistics")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Status", "✅ Initialized" if graph_info.get('is_initialized') else "❌ Not Initialized")
                with col2:
                    st.metric("Working Directory", graph_info.get('working_dir', 'N/A'))
                with col3:
                    st.metric("Last Updated", graph_info.get('timestamp', 'N/A')[:19] if graph_info.get('timestamp') else 'N/A')
                
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
                st.info("ℹ️ No data to display")
    
    with tab5:
        st.header("ℹ️ Application Information")
        
        st.markdown("""
        ### 🧠 Fast GraphRAG Document Analyzer
        
        This application uses **Fast GraphRAG** to intelligently analyze and query documents.
        
        #### ✨ Key Features:
        - 📁 **Multi-format file upload**: TXT, PDF, DOCX, MD
        - 🧠 **Intelligent analysis**: Uses GraphRAG to create knowledge graphs
        - 🔍 **Natural language queries**: Ask questions in Vietnamese and English
        - 📊 **Visualization**: Display relationships between entities
        - 📜 **Query history**: Store and manage previously asked questions
        
        #### 🚀 How to use:
        1. **Configuration**: Enter OpenAI API key and set up domain
        2. **Upload**: Select and upload document files
        3. **Process**: Add documents to GraphRAG
        4. **Query**: Ask questions and receive intelligent answers
        5. **Visualization**: View charts and statistics
        
        #### 🔧 Configuration:
        - **Domain**: Describe the field and analysis objectives
        - **Entity Types**: Types of entities to recognize
        - **Example Queries**: Sample questions to guide AI
        
        #### 📚 Dependencies:
        - Fast GraphRAG: Main framework
        - OpenAI: Language model
        - Streamlit: Web interface
        - Plotly: Visualization
        - NetworkX: Graph processing
        """)
        
        # System info
        st.subheader("🔧 System Information")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **Configuration:**
            - Working Directory: `{Config.WORKING_DIR}`
            - Max File Size: {Config.MAX_FILE_SIZE / (1024*1024):.0f}MB
            - Supported Extensions: {', '.join(Config.ALLOWED_EXTENSIONS)}
            """)
        
        with col2:
            st.markdown(f"""
            **Status:**
            - GraphRAG Initialized: {'✅' if st.session_state.graphrag_handler.is_initialized else '❌'}
            - Files Processed: {len(st.session_state.processed_files)}
            - Queries Made: {len(st.session_state.query_history)}
            """)

if __name__ == "__main__":
    main()
