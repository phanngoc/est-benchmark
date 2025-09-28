# 🧠 Fast GraphRAG Document Analyzer

Ứng dụng Streamlit để test và sử dụng [Fast GraphRAG](https://github.com/circlemind-ai/fast-graphrag) cho việc phân tích và truy vấn nhiều file tài liệu.

## ✨ Tính năng chính

- 📁 **Upload đa dạng loại file**: TXT, PDF, DOCX, MD
- 🧠 **Phân tích thông minh**: Sử dụng Fast GraphRAG để tạo knowledge graph
- 🔍 **Truy vấn tự nhiên**: Hỏi đáp bằng tiếng Việt
- 📊 **Visualization**: Hiển thị mối quan hệ giữa các thực thể
- 📜 **Lịch sử truy vấn**: Lưu trữ và quản lý các câu hỏi đã hỏi
- ⚙️ **Cấu hình linh hoạt**: Tùy chỉnh domain, entity types, example queries

## 🚀 Cài đặt

### 1. Clone repository

```bash
git clone <repository-url>
cd est-benchmark
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu hình môi trường

Tạo file `.env` từ `env.example`:

```bash
cp env.example .env
```

Chỉnh sửa file `.env` và thêm OpenAI API key:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
CONCURRENT_TASK_LIMIT=8
```

### 4. Chạy ứng dụng

```bash
streamlit run app.py
```

Ứng dụng sẽ mở tại `http://localhost:8501`

## 📖 Hướng dẫn sử dụng

### Bước 1: Cấu hình
1. Mở ứng dụng trong trình duyệt
2. Nhập OpenAI API key vào sidebar
3. Thiết lập domain description (mô tả lĩnh vực phân tích)
4. Chọn entity types (các loại thực thể cần nhận diện)
5. Nhập example queries (câu hỏi mẫu)
6. Nhấn "Khởi tạo GraphRAG"

### Bước 2: Upload tài liệu
1. Chuyển đến tab "Upload Files"
2. Chọn các file cần phân tích (TXT, PDF, DOCX, MD)
3. Nhấn "Xử lý Files" để trích xuất nội dung
4. Nhấn "Thêm vào GraphRAG" để xử lý

### Bước 3: Truy vấn
1. Chuyển đến tab "Query"
2. Nhập câu hỏi của bạn
3. Chọn có hiển thị references hay không
4. Nhấn "Tìm kiếm" để nhận câu trả lời

### Bước 4: Visualization
1. Chuyển đến tab "Visualization"
2. Xem thống kê và biểu đồ về dữ liệu đã xử lý

## 📁 Cấu trúc dự án

```
est-benchmark/
├── app.py                 # Ứng dụng Streamlit chính
├── config.py             # Cấu hình
├── requirements.txt      # Dependencies
├── env.example          # Mẫu file môi trường
├── utils/               # Utility modules
│   ├── __init__.py
│   ├── file_processor.py  # Xử lý file upload
│   ├── graphrag_handler.py # Wrapper cho Fast GraphRAG
│   └── visualization.py   # Hiển thị graph
├── examples/            # Tài liệu mẫu
│   └── sample_docs/
│       ├── sample1.txt
│       ├── sample2.txt
│       ├── sample3.txt
│       └── README.md
└── README.md
```

## 🔧 Cấu hình nâng cao

### Entity Types mặc định
- Person: Người
- Organization: Tổ chức
- Location: Địa điểm
- Concept: Khái niệm
- Event: Sự kiện
- Document: Tài liệu
- Topic: Chủ đề

### Example Queries mặc định
- "Tài liệu này nói về chủ đề gì?"
- "Có những nhân vật chính nào được đề cập?"
- "Mối quan hệ giữa các thực thể là gì?"
- "Những sự kiện quan trọng nào được mô tả?"
- "Tài liệu này có những thông tin gì quan trọng?"

## 📚 Dependencies

- **streamlit**: Web interface
- **fast-graphrag**: GraphRAG framework
- **openai**: Language model API
- **python-dotenv**: Environment variables
- **pandas**: Data manipulation
- **plotly**: Visualization
- **networkx**: Graph processing
- **PyPDF2**: PDF processing
- **python-docx**: DOCX processing
- **markdown**: Markdown processing

## 🎯 Use Cases

### 1. Phân tích tài liệu học thuật
- Upload các bài nghiên cứu, luận văn
- Tìm kiếm thông tin liên quan đến chủ đề cụ thể
- Phân tích mối quan hệ giữa các khái niệm

### 2. Xử lý tài liệu doanh nghiệp
- Upload báo cáo, hợp đồng, tài liệu pháp lý
- Tìm kiếm thông tin nhanh chóng
- Phân tích nội dung và xu hướng

### 3. Nghiên cứu thị trường
- Upload các báo cáo thị trường
- Phân tích xu hướng và cơ hội
- So sánh các công ty và sản phẩm

### 4. Giáo dục và đào tạo
- Upload tài liệu học tập
- Tạo hệ thống hỏi đáp thông minh
- Phân tích nội dung khóa học

## 🐛 Troubleshooting

### Lỗi API Key
- Đảm bảo đã nhập đúng OpenAI API key
- Kiểm tra API key có đủ quota không

### Lỗi xử lý file
- Kiểm tra file có đúng định dạng không
- Đảm bảo file không quá lớn (giới hạn 200MB)

### Lỗi GraphRAG
- Đảm bảo đã khởi tạo GraphRAG trước khi sử dụng
- Kiểm tra cấu hình domain và entity types

## 🤝 Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng:

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📄 License

Dự án này được phân phối dưới MIT License. Xem file `LICENSE` để biết thêm chi tiết.

## 🙏 Acknowledgments

- [Fast GraphRAG](https://github.com/circlemind-ai/fast-graphrag) - Framework chính
- [Streamlit](https://streamlit.io/) - Web framework
- [OpenAI](https://openai.com/) - Language model API

## 📞 Liên hệ

Nếu có câu hỏi hoặc góp ý, vui lòng tạo issue trên GitHub repository.
