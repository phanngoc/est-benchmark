import os
import io
import streamlit as st
from typing import List, Dict, Any, Optional
import PyPDF2
from docx import Document
import markdown

class FileProcessor:
    """Class để xử lý các loại file khác nhau"""
    
    SUPPORTED_EXTENSIONS = {
        '.txt': 'text/plain',
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.md': 'text/markdown'
    }
    
    @staticmethod
    def extract_text_from_file(file_content: bytes, filename: str) -> str:
        """Trích xuất text từ file content"""
        file_ext = os.path.splitext(filename)[1].lower()
        
        try:
            if file_ext == '.txt':
                return file_content.decode('utf-8')
            
            elif file_ext == '.pdf':
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
            
            elif file_ext == '.docx':
                doc = Document(io.BytesIO(file_content))
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            
            elif file_ext == '.md':
                # Convert markdown to plain text
                md_text = file_content.decode('utf-8')
                html = markdown.markdown(md_text)
                # Simple HTML to text conversion
                import re
                text = re.sub(r'<[^>]+>', '', html)
                return text
            
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
                
        except Exception as e:
            st.error(f"Lỗi khi xử lý file {filename}: {str(e)}")
            return ""
    
    @staticmethod
    def validate_file(file) -> Dict[str, Any]:
        """Validate file upload"""
        result = {
            'valid': True,
            'error': None,
            'size_mb': 0
        }
        
        # Check file size
        file_size = len(file.getvalue())
        result['size_mb'] = file_size / (1024 * 1024)
        
        if result['size_mb'] > 200:  # 200MB limit
            result['valid'] = False
            result['error'] = f"File quá lớn ({result['size_mb']:.1f}MB). Giới hạn 200MB."
            return result
        
        # Check file extension
        file_ext = os.path.splitext(file.name)[1].lower()
        if file_ext not in FileProcessor.SUPPORTED_EXTENSIONS:
            result['valid'] = False
            result['error'] = f"Loại file không được hỗ trợ: {file_ext}. Chỉ hỗ trợ: {', '.join(FileProcessor.SUPPORTED_EXTENSIONS.keys())}"
        
        return result
    
    @staticmethod
    def process_uploaded_files(uploaded_files: List) -> List[Dict[str, Any]]:
        """Xử lý danh sách file đã upload"""
        processed_files = []
        
        for uploaded_file in uploaded_files:
            # Validate file
            validation = FileProcessor.validate_file(uploaded_file)
            if not validation['valid']:
                st.error(f"File {uploaded_file.name}: {validation['error']}")
                continue
            
            # Extract text
            file_content = uploaded_file.getvalue()
            text = FileProcessor.extract_text_from_file(file_content, uploaded_file.name)
            
            if text.strip():
                processed_files.append({
                    'name': uploaded_file.name,
                    'content': text,
                    'size_mb': validation['size_mb'],
                    'type': os.path.splitext(uploaded_file.name)[1].lower()
                })
            else:
                st.warning(f"Không thể trích xuất text từ file: {uploaded_file.name}")
        
        return processed_files
    
    @staticmethod
    def get_file_preview(content: str, max_chars: int = 500) -> str:
        """Lấy preview của file content"""
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "..."
