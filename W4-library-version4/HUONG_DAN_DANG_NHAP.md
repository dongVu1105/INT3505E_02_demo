# 🔐 HƯỚNG DẪN ĐĂNG NHẬP - LIBRARY MANAGEMENT SYSTEM

## ✅ Vấn đề đã được khắc phục

Vấn đề CORS (Cross-Origin Resource Sharing) đã được sửa để cho phép client kết nối với server từ nhiều nguồn khác nhau.

### Thay đổi đã thực hiện:

1. **Cập nhật CORS Configuration trong `server/app.py`**
   - Cho phép tất cả origins (`*`) trong môi trường development
   - Cho phép các methods: GET, POST, PUT, DELETE, OPTIONS
   - Cho phép headers: Content-Type, Authorization

2. **Cập nhật file `.env` và `.env.example`**
   - Thêm nhiều origins phổ biến: localhost:3000, :5500, :8080
   - Thêm `null` để hỗ trợ file:// protocol

3. **Server đã chạy thành công**
   - URL: `http://localhost:5000`
   - API Endpoints: `http://localhost:5000/api`

---

## 📋 HƯỚNG DẪN SỬ DỤNG

### Bước 1: Khởi động Server (Đã hoàn thành ✓)

Server REST API đã đang chạy tại `http://localhost:5000`

Bạn có thể thấy thông báo như sau:
```
🚀 Library Management REST API Server
Server running on: http://localhost:5000
API Endpoints: http://localhost:5000/api
```

### Bước 2: Mở Client Application

**QUAN TRỌNG:** Bạn cần mở file HTML qua HTTP server, không phải mở trực tiếp file.

#### Cách 1: Sử dụng Live Server extension trong VS Code (Khuyến nghị)

1. Cài đặt extension "Live Server" trong VS Code nếu chưa có
2. Click chuột phải vào file `client/index.html`
3. Chọn "Open with Live Server"
4. Browser sẽ tự động mở tại `http://localhost:5500` hoặc `http://127.0.0.1:5500`

#### Cách 2: Sử dụng Python HTTP Server

Mở terminal mới và chạy:
```powershell
cd d:\KTHDV\INT3505E_02_demo\W4-library-version5\client
python -m http.server 8080
```

Sau đó mở browser và truy cập: `http://localhost:8080`

#### Cách 3: Sử dụng Node.js http-server

```powershell
cd d:\KTHDV\INT3505E_02_demo\W4-library-version5\client
npx http-server -p 8080
```

Sau đó mở browser và truy cập: `http://localhost:8080`

### Bước 3: Đăng nhập

1. Trang login sẽ hiển thị với form đăng nhập
2. **DEMO MODE**: Chương trình chấp nhận BẤT KỲ username và password nào
   - Username mặc định: `admin`
   - Password mặc định: `password123`
   - Hoặc bạn có thể nhập bất kỳ giá trị nào

3. Click nút "Login & Get JWT Token"

4. Nếu thành công:
   - JWT Token sẽ được hiển thị
   - Token được lưu vào localStorage
   - Tự động chuyển sang Dashboard sau 1.5 giây

5. Bây giờ bạn có thể:
   - Xem Dashboard với thống kê
   - Quản lý sách (Books)
   - Quản lý phiếu mượn (Borrow Records)

---

## 🔧 KIỂM TRA XEM SERVER CÓ HOẠT ĐỘNG KHÔNG

Mở browser và truy cập: `http://localhost:5000`

Bạn sẽ thấy response JSON như sau:
```json
{
  "success": true,
  "service": "Library Management REST API",
  "version": "3.0.0",
  "description": "REST API Server cho hệ thống quản lý thư viện",
  "endpoints": {
    "auth": "/api/auth/login",
    "books": "/api/books",
    ...
  }
}
```

Hoặc test login endpoint bằng curl/Postman:
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"password123\"}"
```

---

## 🐛 TROUBLESHOOTING

### Lỗi: "Connection error" hoặc "CORS error"

**Nguyên nhân:** Bạn mở file HTML trực tiếp (file://) thay vì qua HTTP server

**Giải pháp:** Sử dụng một trong 3 cách ở Bước 2 để mở client qua HTTP server

### Lỗi: "Network Error" hoặc không kết nối được

**Kiểm tra:**
1. Server có đang chạy không? (Xem terminal có thông báo "Running on http://localhost:5000")
2. Firewall có chặn port 5000 không?
3. Thử truy cập trực tiếp `http://localhost:5000` trong browser

### Lỗi: "Token is invalid or expired"

**Giải pháp:**
1. Click nút "Logout"
2. Đăng nhập lại
3. Token mới sẽ được tạo với thời gian hiệu lực 24 giờ

---

## 📚 KIẾN TRÚC REST API

Ứng dụng này minh họa kiến trúc **Client-Server** theo nguyên tắc REST:

✅ **Stateless**: Server không lưu session, sử dụng JWT token
✅ **Client-Server**: Tách biệt hoàn toàn UI (client) và API (server)
✅ **Uniform Interface**: HTTP methods chuẩn (GET, POST, PUT, DELETE)
✅ **Resource-based**: URL định danh resources (/api/books, /api/borrow-records)
✅ **JSON representation**: Dữ liệu trao đổi qua JSON
✅ **Cacheable**: Sử dụng Cache-Control, ETag, conditional requests

---

## 🎯 DEMO CREDENTIALS

Chương trình ở chế độ DEMO, chấp nhận mọi username/password:

**Mặc định:**
- Username: `admin`
- Password: `password123`

**Hoặc tự do nhập:**
- Username: bất kỳ
- Password: bất kỳ

---

## 📞 HỖ TRỢ

Nếu vẫn gặp vấn đề, hãy:
1. Kiểm tra Console của Browser (F12) để xem lỗi chi tiết
2. Kiểm tra Terminal chạy server để xem log
3. Đảm bảo cả server và client đều chạy qua HTTP (không phải file://)

Chúc bạn thành công! 🚀
