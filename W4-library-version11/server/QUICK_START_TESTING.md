# Quick Start Guide - Testing

## Cài đặt nhanh

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Đảm bảo MongoDB đang chạy
```bash
# Kiểm tra MongoDB
mongosh mongodb://root:root@localhost:27017
```

## Chạy Tests

### Cách 1: Sử dụng unittest (Khuyến nghị cho Windows)
```bash
# Chạy tất cả tests
python -m unittest test_api.py

# Chạy với verbose
python -m unittest test_api.py -v

# Chạy một test class cụ thể
python -m unittest test_api.TestAuthenticationEndpoints

# Chạy một test method cụ thể
python -m unittest test_api.TestAuthenticationEndpoints.test_login_success
```

### Cách 2: Sử dụng batch script (Windows)
```bash
# Chạy tất cả tests
run_tests.bat

# Chạy với coverage report
run_tests.bat coverage

# Chạy verbose mode
run_tests.bat verbose

# Chạy fast mode với pytest
run_tests.bat fast
```

### Cách 3: Sử dụng Python script
```bash
# Chạy tất cả tests
python run_tests.py

# Chạy với coverage
python run_tests.py --mode coverage

# Chạy verbose
python run_tests.py --mode verbose

# Chạy specific class
python run_tests.py --class TestBooksEndpoints

# Chạy specific method
python run_tests.py --class TestBooksEndpoints --method test_create_book_success
```

### Cách 4: Sử dụng pytest (Nếu đã cài)
```bash
# Chạy tất cả tests
pytest test_api.py -v

# Chạy với coverage
pytest test_api.py --cov=. --cov-report=html

# Chạy tests matching pattern
pytest test_api.py -k "test_login"
```

## Test Coverage Summary

### Authentication (10 tests)
- Login/Logout
- Token verification
- Authorization checks

### Books (25 tests)
- CRUD operations
- Pagination & filtering
- Sorting
- Validation & error handling

### Borrow Records (15 tests)
- Create/Read operations
- Return books
- Inventory management
- Validation

### Statistics (2 tests)
- System statistics
- Empty database handling

### Health & Cache (6 tests)
- Health check
- Cache behavior
- ETag support

### Error Handling (3 tests)
- 404, 405 errors
- Invalid JSON

### Root Endpoint (1 test)
- API information

**Total: 72+ test cases**

## Xem Coverage Report

Sau khi chạy với coverage:
```bash
# Mở HTML report
start htmlcov\index.html    # Windows
open htmlcov/index.html     # Mac/Linux
```

## Troubleshooting

### MongoDB không kết nối được
```bash
# Kiểm tra MongoDB service
net start MongoDB

# Hoặc khởi động Docker container
docker run -d -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=root mongo
```

### Test database không cleanup
```python
# Chạy cleanup script
from pymongo import MongoClient
client = MongoClient('mongodb://root:root@localhost:27017')
client.drop_database('library-test')
```

### Import errors
```bash
# Re-install dependencies
pip install --upgrade -r requirements.txt
```

## Test Structure

```
server/
├── test_api.py              # Main test file
├── run_tests.py             # Python test runner
├── run_tests.bat            # Windows batch script
├── pytest.ini               # Pytest configuration
├── README_TESTING.md        # Detailed testing guide
└── QUICK_START_TESTING.md   # This file
```

## Next Steps

1. Chạy tests để verify setup: `python -m unittest test_api.py`
2. Xem coverage report: `run_tests.bat coverage`
3. Tích hợp vào CI/CD pipeline
4. Thêm tests mới khi có features mới

## Tips

- Chạy tests thường xuyên khi develop
- Aim for >80% code coverage
- Viết test trước khi fix bug (TDD)
- Keep tests fast và independent
- Use descriptive test names
