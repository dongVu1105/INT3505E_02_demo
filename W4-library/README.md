# 📚 Hệ Thống Quản Lý Thư Viện

Hệ thống quản lý thư viện đơn giản được xây dựng bằng Flask, hỗ trợ quản lý sách và mượn/trả sách.

## 🌟 Tính năng

### Quản lý sách
- ✅ Xem danh sách tất cả sách
- ➕ Thêm sách mới
- ✏️ Chỉnh sửa thông tin sách
- 🗑️ Xóa sách (chỉ khi không có sách đang được mượn)
- 📊 Theo dõi số lượng sách có sẵn và đã mượn

### Quản lý mượn/trả sách
- 📤 Mượn sách
- ✅ Trả sách
- 📋 Xem lịch sử mượn/trả
- 🔍 Lọc theo trạng thái (đang mượn/đã trả)

### Dashboard
- 📈 Thống kê tổng quan
- 📊 Số lượng sách trong hệ thống
- 📚 Số sách đang được mượn
- 📖 Tổng số lượt mượn

## 🛠️ Công nghệ sử dụng

- **Backend**: Flask 3.0.0
- **Database**: SQLite với Flask-SQLAlchemy
- **Frontend**: HTML5, CSS3
- **Template Engine**: Jinja2

## 📋 Yêu cầu hệ thống

- Python 3.7 trở lên
- pip (Python package installer)

## 🚀 Hướng dẫn cài đặt

### 1. Clone hoặc tải về project

```bash
cd W4-library
```

### 2. Tạo môi trường ảo (khuyến nghị)

**Trên Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**Trên macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Cài đặt các thư viện cần thiết

```bash
pip install -r requirements.txt
```

### 4. Chạy ứng dụng

```bash
python app.py
```

### 5. Truy cập ứng dụng

Mở trình duyệt và truy cập:
```
http://localhost:5000
```

## 📁 Cấu trúc thư mục

```
W4-library/
│
├── app.py                 # File chính của ứng dụng Flask
├── models.py              # Định nghĩa models (Book, BorrowRecord)
├── requirements.txt       # Danh sách thư viện Python cần thiết
├── README.md             # File hướng dẫn này
│
├── templates/            # Thư mục chứa HTML templates
│   ├── base.html        # Template cơ sở
│   ├── index.html       # Trang chủ
│   ├── books.html       # Danh sách sách
│   ├── add_book.html    # Form thêm sách
│   ├── edit_book.html   # Form sửa sách
│   ├── borrow_book.html # Form mượn sách
│   └── borrow_records.html # Lịch sử mượn/trả
│
├── static/              # Thư mục chứa file tĩnh
│   └── css/
│       └── style.css    # File CSS
│
└── library.db           # Database SQLite (tự động tạo khi chạy app)
```

## 💾 Database Schema

### Book (Sách)
- `id`: ID sách (Primary Key)
- `title`: Tên sách
- `author`: Tác giả
- `isbn`: Mã ISBN (13 chữ số, unique)
- `quantity`: Tổng số lượng sách
- `available`: Số lượng sách còn lại có thể mượn
- `created_at`: Ngày tạo

### BorrowRecord (Bản ghi mượn sách)
- `id`: ID bản ghi (Primary Key)
- `book_id`: ID sách (Foreign Key)
- `borrower_name`: Tên người mượn
- `borrower_email`: Email người mượn
- `borrow_date`: Ngày mượn
- `return_date`: Ngày trả (NULL nếu chưa trả)
- `status`: Trạng thái ('borrowed' hoặc 'returned')

## 📝 Hướng dẫn sử dụng

### Thêm sách mới
1. Vào menu "Quản lý sách"
2. Click nút "➕ Thêm sách mới"
3. Điền đầy đủ thông tin: Tên sách, Tác giả, ISBN (13 số), Số lượng
4. Click "💾 Lưu sách"

### Mượn sách
1. Vào menu "Quản lý sách"
2. Chọn sách muốn mượn (phải còn sách available)
3. Click nút "📤 Mượn"
4. Điền thông tin người mượn (tên và email)
5. Click "✅ Xác nhận mượn"

### Trả sách
1. Vào menu "Mượn/Trả sách"
2. Tìm bản ghi mượn sách cần trả
3. Click nút "✅ Xác nhận trả"

### Chỉnh sửa sách
1. Vào menu "Quản lý sách"
2. Click nút "✏️ Sửa" ở sách cần chỉnh sửa
3. Cập nhật thông tin
4. Click "💾 Cập nhật"

### Xóa sách
1. Vào menu "Quản lý sách"
2. Click nút "🗑️ Xóa" ở sách cần xóa
3. Xác nhận xóa (chỉ xóa được khi không có sách đang được mượn)

## ⚠️ Lưu ý

- ISBN phải là duy nhất và có đúng 13 chữ số
- Không thể xóa sách đang có người mượn
- Số lượng sách phải đủ để mượn (available > 0)
- Database SQLite được lưu trong file `library.db`

## 🎨 Giao diện

- Giao diện responsive, tương thích với mobile
- Sử dụng màu sắc gradient tím đẹp mắt
- Có thông báo flash messages cho các thao tác
- Hiển thị badge trạng thái rõ ràng

## 🔧 Tùy chỉnh

### Thay đổi Secret Key
Trong file `app.py`, thay đổi SECRET_KEY:
```python
app.config['SECRET_KEY'] = 'your-new-secret-key-here'
```

### Thay đổi Database
Mặc định sử dụng SQLite. Để dùng database khác, sửa `SQLALCHEMY_DATABASE_URI` trong `app.py`.

## 🐛 Debug Mode

Ứng dụng chạy ở chế độ debug mặc định:
```python
app.run(debug=True)
```

Để chạy production, đổi thành:
```python
app.run(debug=False)
```

## 📧 Liên hệ

Nếu có bất kỳ câu hỏi hoặc góp ý nào, vui lòng liên hệ!

---

**Chúc bạn sử dụng hệ thống thành công! 🎉**
