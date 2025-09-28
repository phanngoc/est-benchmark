#!/usr/bin/env python3
"""
Script để chạy ứng dụng Fast GraphRAG Streamlit
"""

import subprocess
import sys
import os

def main():
    """Chạy ứng dụng Streamlit"""
    
    # Kiểm tra xem có file .env không
    if not os.path.exists('.env'):
        print("⚠️  Chưa có file .env. Vui lòng tạo từ env.example và cấu hình OpenAI API key.")
        print("   cp env.example .env")
        print("   Sau đó chỉnh sửa file .env với API key của bạn.")
        return
    
    # Kiểm tra dependencies
    try:
        import streamlit
        import fast_graphrag
        import openai
    except ImportError as e:
        print(f"❌ Thiếu dependency: {e}")
        print("Vui lòng cài đặt: pip install -r requirements.txt")
        return
    
    print("🚀 Đang khởi động Fast GraphRAG Document Analyzer...")
    print("📱 Ứng dụng sẽ mở tại: http://localhost:8501")
    print("🛑 Nhấn Ctrl+C để dừng ứng dụng")
    print("-" * 50)
    
    try:
        # Chạy streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8505",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n👋 Đã dừng ứng dụng. Tạm biệt!")
    except Exception as e:
        print(f"❌ Lỗi khi chạy ứng dụng: {e}")

if __name__ == "__main__":
    main()
