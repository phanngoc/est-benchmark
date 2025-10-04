# ChromaDB Manager Tool

## 📖 Giới thiệu

ChromaDB Manager là công cụ quản lý ChromaDB với giao diện Streamlit đầy đủ tính năng CRUD (Create, Read, Update, Delete) và Query Panel mạnh mẽ.

## ✨ Tính năng

### 1. 📚 Quản lý Collections
- ✅ Xem danh sách tất cả collections
- ✅ Tạo collection mới với metadata tùy chỉnh
- ✅ Xóa collection
- ✅ Xem thông tin chi tiết từng collection (số lượng documents, metadata)

### 2. 📄 Quản lý Documents
- ✅ **Xem tất cả documents**: Hiển thị dạng table, export CSV
- ✅ **Thêm mới**: 
  - Single document với metadata
  - Batch import từ JSON
- ✅ **Cập nhật**: Chỉnh sửa document và metadata
- ✅ **Xóa**: Xóa từng document hoặc xóa nhiều documents

### 3. 🔍 Query Panel
- ✅ **Semantic Search**: Tìm kiếm documents tương tự dựa trên nội dung
- ✅ **Filter by Metadata**: Lọc theo điều kiện metadata
- ✅ **Advanced Query**: Kết hợp semantic search và metadata filter

## 🚀 Cách sử dụng

### 1. Cài đặt dependencies

Đảm bảo đã cài đặt các packages cần thiết (đã có trong `requirements.txt`):

```bash
pip install streamlit chromadb pandas
```

### 2. Chạy ứng dụng

```bash
# Từ thư mục gốc của project
streamlit run tools/chromadb_manager.py

# Hoặc từ thư mục tools
cd tools
streamlit run chromadb_manager.py
```

### 3. Cấu hình Database Path

Trong sidebar, bạn có thể:
- Nhập custom path cho database
- Hoặc chọn từ các path có sẵn:
  - `./estimation_history_db` (default - dùng cho estimation history)
  - `./chroma_db`
  - `./data/chroma`

## 📋 Hướng dẫn chi tiết

### Collection Management

#### Tạo Collection mới
1. Vào tab "📚 Collections"
2. Nhập tên collection
3. (Optional) Nhập mô tả metadata
4. Click "➕ Tạo Collection"

#### Xóa Collection
1. Tìm collection trong danh sách
2. Click "🗑️ Xóa"
3. Click lại lần nữa để xác nhận

### Document Management

#### Xem Documents
1. Chọn collection từ danh sách
2. Click "🔍 Xem chi tiết"
3. Tab "📋 Xem tất cả" hiển thị table với tất cả documents
4. Export CSV nếu cần

#### Thêm Single Document
1. Tab "➕ Thêm mới"
2. Chọn "Single Document"
3. Nhập:
   - Document ID (unique)
   - Document Content
   - Metadata (JSON format)
4. Click "➕ Thêm Document"

#### Batch Import
1. Tab "➕ Thêm mới"
2. Chọn "Batch Import (JSON)"
3. Nhập JSON array theo format:
```json
[
  {
    "id": "doc1",
    "document": "Nội dung document 1",
    "metadata": {"key": "value"}
  },
  {
    "id": "doc2",
    "document": "Nội dung document 2",
    "metadata": {"category": "Backend"}
  }
]
```
4. Click "📥 Import Batch"

#### Update Document
1. Tab "✏️ Cập nhật"
2. Chọn Document ID từ dropdown
3. Xem dữ liệu hiện tại
4. Chỉnh sửa Document Content và Metadata
5. Click "💾 Cập nhật"

#### Delete Documents
1. Tab "🗑️ Xóa"
2. Chọn mode:
   - **Xóa từng document**: Chọn 1 document và xóa
   - **Xóa nhiều documents**: Chọn nhiều documents (multiselect) và xóa hàng loạt

### Query Panel

#### Semantic Search
1. Click "🔍 Query Panel" cho collection
2. Tab "🔎 Semantic Search"
3. Nhập text cần tìm
4. Chọn số lượng kết quả (1-50)
5. Click "🔍 Tìm kiếm"
6. Xem kết quả với distance score (càng nhỏ càng tương đồng)

**Ví dụ:**
```
Text: "Tạo API endpoint để lấy danh sách users"
→ Tìm các documents về API, users, backend tasks tương tự
```

#### Filter by Metadata
1. Tab "🎯 Filter by Metadata"
2. Nhập filter JSON:

**Simple filter:**
```json
{"category": "Backend"}
```

**AND condition:**
```json
{"$and": [{"priority": "High"}, {"status": "pending"}]}
```

**OR condition:**
```json
{"$or": [{"category": "Frontend"}, {"category": "Backend"}]}
```

3. Click "🎯 Lọc"

#### Advanced Query
1. Tab "📊 Advanced Query"
2. Nhập:
   - Query text (để semantic search)
   - Where filter (JSON) - để lọc metadata
   - Số kết quả
3. Click "🚀 Query"
4. Xem kết quả kết hợp cả semantic similarity và metadata filter

**Ví dụ:**
```
Query text: "authentication login security"
Where filter: {"priority": "High"}
→ Tìm các documents về authentication có priority High
```

## 🎯 Use Cases

### 1. Quản lý Estimation History
- Xem tất cả estimations đã lưu
- Tìm kiếm estimations tương tự cho tasks mới
- Filter theo category, priority, complexity
- Update estimations khi có feedback

### 2. Debugging ChromaDB
- Kiểm tra dữ liệu đã được lưu đúng chưa
- Xem embeddings có được generate không
- Test query results
- Verify metadata structure

### 3. Data Analysis
- Export data ra CSV để phân tích
- Xem distribution của categories
- Tìm patterns trong estimations
- Validate data quality

### 4. Data Cleaning
- Tìm và xóa duplicate documents
- Update sai metadata
- Remove outdated estimations
- Batch update documents

## 📊 Giao diện

### Sidebar
- **Database Configuration**: Chọn/nhập database path
- **Quick Stats**: Xem nhanh số collections và documents
- **Navigation**: Di chuyển giữa các tabs

### Main Tabs
1. **Collections**: Quản lý collections
2. **Documents**: CRUD operations cho documents
3. **Query Panel**: Semantic search và filtering

## 🔧 Technical Details

### ChromaDB Features Used
- `PersistentClient`: Lưu trữ persistent
- `get_or_create_collection`: Quản lý collections
- `query()`: Semantic search với embeddings
- `get()`: Retrieve documents
- `add()`, `update()`, `delete()`: CRUD operations

### Data Structure
```python
Document = {
    "id": str,              # Unique identifier
    "document": str,        # Text content
    "metadata": dict,       # Arbitrary key-value pairs
    "embedding": List[float]  # Auto-generated by ChromaDB
}
```

### Metadata Best Practices
- Sử dụng consistent keys (category, priority, status, etc.)
- Values có thể là: string, int, float, bool
- Tránh nested objects (ChromaDB không hỗ trợ)
- JSON serialize cho complex data

## 🎨 Tips & Tricks

### 1. Semantic Search hiệu quả
- Viết query text chi tiết, rõ ràng
- Sử dụng keywords quan trọng
- Test với nhiều variations
- Adjust n_results để tìm sweet spot

### 2. Metadata Filter
- Thiết kế metadata schema trước
- Sử dụng consistent values
- Combine với semantic search cho best results

### 3. Performance
- ChromaDB nhanh với <10K documents
- Sử dụng batch operations cho bulk insert
- Cache query results nếu query lặp lại

### 4. Data Management
- Export CSV định kỳ để backup
- Document naming convention: `project_timestamp_id`
- Xóa old data để giữ DB nhẹ

## 🐛 Troubleshooting

### Không kết nối được ChromaDB
- Kiểm tra path có đúng không
- Đảm bảo có quyền write vào thư mục
- Thử tạo path mới

### Query không trả về kết quả
- Kiểm tra collection có documents không
- Verify query text có ý nghĩa
- Thử giảm threshold hoặc tăng n_results

### Metadata filter không hoạt động
- Kiểm tra JSON syntax
- Verify keys có tồn tại trong documents
- Check data types khớp

## 📝 Examples

### Example 1: Import Estimation Data
```json
[
  {
    "id": "est_001",
    "document": "Create user authentication API with JWT tokens",
    "metadata": {
      "category": "Backend",
      "priority": "High",
      "estimation_manday": 3.0,
      "confidence_level": 0.8
    }
  },
  {
    "id": "est_002",
    "document": "Design responsive login page with validation",
    "metadata": {
      "category": "Frontend",
      "priority": "High",
      "estimation_manday": 2.5,
      "confidence_level": 0.75
    }
  }
]
```

### Example 2: Query Similar Tasks
```
Query: "user management CRUD operations"
Filter: {"category": "Backend"}
Results: All backend tasks related to user CRUD
```

### Example 3: Find High Priority Tasks
```json
{"$and": [
  {"priority": "High"},
  {"estimation_manday": {"$gte": 2.0}}
]}
```

## 🚀 Next Steps

Sau khi làm quen với tool, bạn có thể:
1. Integrate vào workflow estimation
2. Tự động import estimation results
3. Build dashboard analytics
4. Create custom query templates
5. Export data cho ML training

## 📚 Tài liệu tham khảo

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- Project's `config.py` cho default settings
- Project's `utils/estimation_history_manager.py` để xem cách sử dụng programmatic

---

**Made with ❤️ for easy ChromaDB management**
