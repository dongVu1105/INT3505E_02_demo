# Unit Testing cho Library Management REST API

## Tổng quan

File `test_api.py` chứa unit tests toàn diện cho tất cả các endpoints của REST API, bao gồm:

### 1. Authentication Tests (TestAuthenticationEndpoints)
- ✅ Đăng nhập thành công
- ✅ Đăng nhập với dữ liệu thiếu (username/password)
- ✅ Đăng xuất
- ✅ Verify token hợp lệ/không hợp lệ/hết hạn
- ✅ Kiểm tra token từ cookie và Authorization header

### 2. Books CRUD Tests (TestBooksEndpoints)
- ✅ GET: Lấy danh sách sách (rỗng, có dữ liệu)
- ✅ GET: Pagination (phân trang)
- ✅ GET: Filtering (author, title, ISBN, available_only)
- ✅ GET: Sorting (asc/desc)
- ✅ GET: Lấy sách theo ID
- ✅ POST: Tạo sách mới
- ✅ POST: Validation (thiếu fields, ISBN trùng, quantity không hợp lệ)
- ✅ PUT: Cập nhật sách
- ✅ PUT: Cập nhật quantity với sách đang được mượn
- ✅ DELETE: Xóa sách
- ✅ DELETE: Không cho xóa sách đang được mượn
- ✅ Authorization checks cho tất cả mutations

### 3. Borrow Records Tests (TestBorrowRecordsEndpoints)
- ✅ GET: Lấy danh sách borrow records
- ✅ GET: Filtering theo status, borrower_name, borrower_email
- ✅ GET: Lấy borrow record theo ID
- ✅ POST: Tạo borrow record mới
- ✅ POST: Kiểm tra available inventory
- ✅ PUT: Trả sách
- ✅ PUT: Không cho trả sách đã trả
- ✅ Authorization checks

### 4. Statistics Tests (TestStatisticsEndpoint)
- ✅ Thống kê với database rỗng
- ✅ Thống kê với dữ liệu (books, copies, borrow records)

### 5. Health Check Tests (TestHealthCheckEndpoint)
- ✅ Kiểm tra health status

### 6. Cache Behavior Tests (TestCacheBehavior)
- ✅ Cache headers trên GET requests
- ✅ ETag và 304 Not Modified
- ✅ Private cache cho authenticated endpoints
- ✅ No-cache cho mutation operations

### 7. Error Handling Tests (TestErrorHandling)
- ✅ 404 Not Found
- ✅ 405 Method Not Allowed
- ✅ Invalid JSON handling

### 8. Root Endpoint Tests (TestRootEndpoint)
- ✅ API information endpoint

## Cài đặt

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2. Đảm bảo MongoDB đang chạy

Test suite cần MongoDB đang chạy tại:
```
mongodb://root:root@localhost:27017
```

Nếu MongoDB của bạn khác, cập nhật `TestConfig` trong file `test_api.py`:

```python
class TestConfig(Config):
    MONGO_URI = 'mongodb://your-connection-string'
```

## Chạy Tests

### Chạy tất cả tests với unittest

```bash
cd server
python -m unittest test_api.py
```

### Chạy với verbose output

```bash
python -m unittest test_api.py -v
```

### Chạy một test class cụ thể

```bash
python -m unittest test_api.TestAuthenticationEndpoints
```

### Chạy một test method cụ thể

```bash
python -m unittest test_api.TestAuthenticationEndpoints.test_login_success
```

### Chạy với pytest (nếu đã cài)

```bash
pytest test_api.py -v
```

### Chạy với coverage report

```bash
pytest test_api.py --cov=. --cov-report=html
```

## Kết quả mong đợi

Khi chạy tests thành công, bạn sẽ thấy output tương tự:

```
........................................................................
----------------------------------------------------------------------
Ran 72 tests in 5.234s

OK
```

## Test Coverage

Test suite này cover:
- **8 test classes**
- **72+ test cases**
- Tất cả các endpoints chính
- Success cases và error cases
- Authentication và authorization
- Database operations
- Cache behavior
- Edge cases

## Lưu ý quan trọng

1. **Test Database**: Tests sử dụng database `library-test`, tách biệt với database production
2. **Auto Cleanup**: Mỗi test tự động cleanup data sau khi chạy
3. **Isolation**: Mỗi test độc lập, không ảnh hưởng lẫn nhau
4. **MongoDB Required**: Cần MongoDB đang chạy để tests hoạt động

## Cấu trúc Test

Mỗi test case tuân theo pattern:
1. **Arrange**: Setup dữ liệu test
2. **Act**: Thực hiện action (API call)
3. **Assert**: Kiểm tra kết quả

Example:
```python
def test_create_book_success(self):
    # Arrange
    book_data = {
        'title': 'New Book',
        'author': 'New Author',
        'isbn': 'ISBN-NEW-001',
        'quantity': 10
    }
    
    # Act
    response = self.client.post('/api/books',
        data=json.dumps(book_data),
        headers=self.get_auth_headers()
    )
    
    # Assert
    self.assertEqual(response.status_code, 201)
    data = json.loads(response.data)
    self.assertTrue(data['success'])
    self.assertEqual(data['data']['title'], 'New Book')
```

## Troubleshooting

### MongoDB Connection Error
```
Error: Could not connect to MongoDB
```
**Giải pháp**: Đảm bảo MongoDB đang chạy và connection string đúng

### Import Error
```
ModuleNotFoundError: No module named 'flask'
```
**Giải pháp**: Chạy `pip install -r requirements.txt`

### Test Database không tự cleanup
**Giải pháp**: Xóa thủ công:
```python
from pymongo import MongoClient
client = MongoClient('mongodb://root:root@localhost:27017')
client.drop_database('library-test')
```

## Mở rộng Tests

Để thêm tests mới:

1. Tạo test method trong class phù hợp
2. Tuân theo naming convention: `test_<feature>_<scenario>`
3. Sử dụng helper methods có sẵn: `create_test_book()`, `create_test_borrow_record()`
4. Cleanup không cần thiết vì `tearDown()` tự động cleanup

## CI/CD Integration

Để tích hợp vào CI/CD pipeline:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mongodb:
        image: mongo:latest
        ports:
          - 27017:27017
        env:
          MONGO_INITDB_ROOT_USERNAME: root
          MONGO_INITDB_ROOT_PASSWORD: root
    
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          cd server
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd server
          python -m unittest test_api.py
```

## Best Practices Được Áp Dụng

1. ✅ **Isolation**: Mỗi test độc lập
2. ✅ **Repeatability**: Tests có thể chạy lại nhiều lần
3. ✅ **Fast**: Tests chạy nhanh (< 10s)
4. ✅ **Self-checking**: Tự động verify kết quả
5. ✅ **Comprehensive**: Cover cả success và error cases
6. ✅ **Readable**: Tên test rõ ràng, dễ hiểu
7. ✅ **Maintainable**: Sử dụng helper methods, DRY principle
