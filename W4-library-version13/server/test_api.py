"""
Unit Tests cho Library Management REST API

Test Coverage:
- Authentication endpoints (login, logout, verify)
- Books CRUD operations
- Borrow records operations
- Statistics endpoint
- Health check endpoint
- Cache behavior
- Error handling
"""
import unittest
import json
from datetime import datetime, timedelta
from bson import ObjectId
from app import create_app
from models import mongo
from config import Config
from auth import generate_token
import jwt


class TestConfig(Config):
    """Test configuration"""
    TESTING = True
    MONGO_URI = 'mongodb://root:root@localhost:27017/library-test?authSource=admin'
    SECRET_KEY = 'test-secret-key'
    JWT_EXPIRATION_HOURS = 1


class BaseTestCase(unittest.TestCase):
    """Base test case với setup/teardown chung"""
    
    def setUp(self):
        """Khởi tạo test client và database"""
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Clear test database
        self.clear_database()
        
        # Create test token
        self.test_user = 'testuser'
        self.test_token = generate_token(self.test_user)
        
    def tearDown(self):
        """Cleanup sau mỗi test"""
        self.clear_database()
        self.app_context.pop()
    
    def clear_database(self):
        """Xóa toàn bộ dữ liệu test"""
        try:
            mongo.db.books.delete_many({})
            mongo.db.borrow_records.delete_many({})
        except:
            pass
    
    def get_auth_headers(self, token=None):
        """Helper để tạo authentication headers"""
        if token is None:
            token = self.test_token
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def create_test_book(self, **kwargs):
        """Helper để tạo sách test"""
        book_data = {
            'title': kwargs.get('title', 'Test Book'),
            'author': kwargs.get('author', 'Test Author'),
            'isbn': kwargs.get('isbn', f'TEST{datetime.now().timestamp()}'),
            'quantity': kwargs.get('quantity', 5),
            'available': kwargs.get('available', 5),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        result = mongo.db.books.insert_one(book_data)
        return str(result.inserted_id)
    
    def create_test_borrow_record(self, book_id, **kwargs):
        """Helper để tạo borrow record test"""
        record_data = {
            'book_id': ObjectId(book_id),
            'borrower_name': kwargs.get('borrower_name', 'Test Borrower'),
            'borrower_email': kwargs.get('borrower_email', 'test@example.com'),
            'borrow_date': kwargs.get('borrow_date', datetime.utcnow()),
            'return_date': kwargs.get('return_date', None),
            'status': kwargs.get('status', 'borrowed')
        }
        result = mongo.db.borrow_records.insert_one(record_data)
        return str(result.inserted_id)


# ============================================================
# AUTHENTICATION TESTS
# ============================================================

class TestAuthenticationEndpoints(BaseTestCase):
    """Tests cho authentication endpoints"""
    
    def test_login_success(self):
        """Test đăng nhập thành công"""
        response = self.client.post('/api/auth/login',
            data=json.dumps({
                'username': 'testuser',
                'password': 'testpass'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Login successful')
        self.assertEqual(data['data']['username'], 'testuser')
        
        # Kiểm tra JWT token được set trong cookie
        self.assertIn('jwt_token', [cookie.name for cookie in self.client.cookie_jar])
    
    def test_login_missing_username(self):
        """Test đăng nhập thiếu username"""
        response = self.client.post('/api/auth/login',
            data=json.dumps({'password': 'testpass'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_login_missing_password(self):
        """Test đăng nhập thiếu password"""
        response = self.client.post('/api/auth/login',
            data=json.dumps({'username': 'testuser'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_login_no_data(self):
        """Test đăng nhập không gửi data"""
        response = self.client.post('/api/auth/login',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_logout(self):
        """Test đăng xuất"""
        response = self.client.post('/api/auth/logout')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Logout successful')
    
    def test_verify_token_valid(self):
        """Test verify token hợp lệ"""
        response = self.client.get('/api/auth/verify',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['valid'])
        self.assertEqual(data['data']['username'], self.test_user)
    
    def test_verify_token_invalid(self):
        """Test verify token không hợp lệ"""
        response = self.client.get('/api/auth/verify',
            headers=self.get_auth_headers(token='invalid-token')
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_verify_token_expired(self):
        """Test verify token đã hết hạn"""
        # Tạo token đã expired
        payload = {
            'username': 'testuser',
            'exp': datetime.utcnow() - timedelta(hours=1),
            'iat': datetime.utcnow() - timedelta(hours=2)
        }
        expired_token = jwt.encode(payload, TestConfig.SECRET_KEY, algorithm='HS256')
        
        response = self.client.get('/api/auth/verify',
            headers=self.get_auth_headers(token=expired_token)
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_verify_token_missing(self):
        """Test verify khi không có token"""
        response = self.client.get('/api/auth/verify')
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)


# ============================================================
# BOOKS CRUD TESTS
# ============================================================

class TestBooksEndpoints(BaseTestCase):
    """Tests cho books endpoints"""
    
    def test_get_books_empty(self):
        """Test lấy danh sách sách khi database trống"""
        response = self.client.get('/api/books')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['books']), 0)
        self.assertEqual(data['data']['pagination']['total'], 0)
    
    def test_get_books_with_data(self):
        """Test lấy danh sách sách có dữ liệu"""
        # Tạo test books
        self.create_test_book(title='Book 1', author='Author 1', isbn='ISBN001')
        self.create_test_book(title='Book 2', author='Author 2', isbn='ISBN002')
        
        response = self.client.get('/api/books')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['books']), 2)
        self.assertEqual(data['data']['pagination']['total'], 2)
    
    def test_get_books_pagination(self):
        """Test pagination"""
        # Tạo 15 books
        for i in range(15):
            self.create_test_book(title=f'Book {i}', isbn=f'ISBN{i:03d}')
        
        # Lấy trang 1 với 10 items
        response = self.client.get('/api/books?page=1&per_page=10')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['data']['books']), 10)
        self.assertEqual(data['data']['pagination']['total'], 15)
        self.assertEqual(data['data']['pagination']['pages'], 2)
        self.assertTrue(data['data']['pagination']['has_next'])
        self.assertFalse(data['data']['pagination']['has_prev'])
        
        # Lấy trang 2
        response = self.client.get('/api/books?page=2&per_page=10')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['data']['books']), 5)
        self.assertFalse(data['data']['pagination']['has_next'])
        self.assertTrue(data['data']['pagination']['has_prev'])
    
    def test_get_books_filter_by_author(self):
        """Test filter theo author"""
        self.create_test_book(title='Book 1', author='John Doe', isbn='ISBN001')
        self.create_test_book(title='Book 2', author='Jane Smith', isbn='ISBN002')
        
        response = self.client.get('/api/books?author=John')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['data']['books']), 1)
        self.assertEqual(data['data']['books'][0]['author'], 'John Doe')
    
    def test_get_books_filter_by_title(self):
        """Test filter theo title"""
        self.create_test_book(title='Python Programming', author='Author 1', isbn='ISBN001')
        self.create_test_book(title='Java Programming', author='Author 2', isbn='ISBN002')
        
        response = self.client.get('/api/books?title=Python')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['data']['books']), 1)
        self.assertIn('Python', data['data']['books'][0]['title'])
    
    def test_get_books_filter_by_isbn(self):
        """Test filter theo ISBN"""
        self.create_test_book(title='Book 1', isbn='ISBN001')
        self.create_test_book(title='Book 2', isbn='ISBN002')
        
        response = self.client.get('/api/books?isbn=ISBN001')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['data']['books']), 1)
        self.assertEqual(data['data']['books'][0]['isbn'], 'ISBN001')
    
    def test_get_books_filter_available_only(self):
        """Test filter chỉ sách available"""
        self.create_test_book(title='Available Book', isbn='ISBN001', available=5)
        self.create_test_book(title='Unavailable Book', isbn='ISBN002', available=0)
        
        response = self.client.get('/api/books?available_only=true')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['data']['books']), 1)
        self.assertGreater(data['data']['books'][0]['available'], 0)
    
    def test_get_books_sorting(self):
        """Test sorting"""
        self.create_test_book(title='Zebra Book', isbn='ISBN001')
        self.create_test_book(title='Apple Book', isbn='ISBN002')
        
        # Sort ascending
        response = self.client.get('/api/books?sort_by=title&sort_order=asc')
        data = json.loads(response.data)
        
        self.assertEqual(data['data']['books'][0]['title'], 'Apple Book')
        self.assertEqual(data['data']['books'][1]['title'], 'Zebra Book')
        
        # Sort descending
        response = self.client.get('/api/books?sort_by=title&sort_order=desc')
        data = json.loads(response.data)
        
        self.assertEqual(data['data']['books'][0]['title'], 'Zebra Book')
        self.assertEqual(data['data']['books'][1]['title'], 'Apple Book')
    
    def test_get_book_by_id(self):
        """Test lấy thông tin một cuốn sách"""
        book_id = self.create_test_book(title='Test Book', isbn='ISBN001')
        
        response = self.client.get(f'/api/books/{book_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['id'], book_id)
        self.assertEqual(data['data']['title'], 'Test Book')
    
    def test_get_book_not_found(self):
        """Test lấy sách không tồn tại"""
        fake_id = str(ObjectId())
        response = self.client.get(f'/api/books/{fake_id}')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_get_book_invalid_id(self):
        """Test lấy sách với ID không hợp lệ"""
        response = self.client.get('/api/books/invalid-id')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_book_success(self):
        """Test tạo sách thành công"""
        book_data = {
            'title': 'New Book',
            'author': 'New Author',
            'isbn': 'ISBN-NEW-001',
            'quantity': 10
        }
        
        response = self.client.post('/api/books',
            data=json.dumps(book_data),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['title'], 'New Book')
        self.assertEqual(data['data']['quantity'], 10)
        self.assertEqual(data['data']['available'], 10)
    
    def test_create_book_unauthorized(self):
        """Test tạo sách khi chưa đăng nhập"""
        book_data = {
            'title': 'New Book',
            'author': 'New Author',
            'isbn': 'ISBN-NEW-001',
            'quantity': 10
        }
        
        response = self.client.post('/api/books',
            data=json.dumps(book_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_book_missing_fields(self):
        """Test tạo sách thiếu thông tin bắt buộc"""
        book_data = {
            'title': 'New Book',
            'author': 'New Author'
            # Missing isbn and quantity
        }
        
        response = self.client.post('/api/books',
            data=json.dumps(book_data),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_book_duplicate_isbn(self):
        """Test tạo sách với ISBN đã tồn tại"""
        self.create_test_book(isbn='DUPLICATE-ISBN')
        
        book_data = {
            'title': 'Another Book',
            'author': 'Another Author',
            'isbn': 'DUPLICATE-ISBN',
            'quantity': 5
        }
        
        response = self.client.post('/api/books',
            data=json.dumps(book_data),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 409)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_book_invalid_quantity(self):
        """Test tạo sách với quantity không hợp lệ"""
        book_data = {
            'title': 'New Book',
            'author': 'New Author',
            'isbn': 'ISBN-NEW-001',
            'quantity': -5
        }
        
        response = self.client.post('/api/books',
            data=json.dumps(book_data),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_update_book_success(self):
        """Test cập nhật sách thành công"""
        book_id = self.create_test_book(title='Old Title', isbn='ISBN001')
        
        update_data = {
            'title': 'New Title',
            'author': 'New Author'
        }
        
        response = self.client.put(f'/api/books/{book_id}',
            data=json.dumps(update_data),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['title'], 'New Title')
        self.assertEqual(data['data']['author'], 'New Author')
    
    def test_update_book_unauthorized(self):
        """Test cập nhật sách khi chưa đăng nhập"""
        book_id = self.create_test_book()
        
        response = self.client.put(f'/api/books/{book_id}',
            data=json.dumps({'title': 'New Title'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_update_book_not_found(self):
        """Test cập nhật sách không tồn tại"""
        fake_id = str(ObjectId())
        
        response = self.client.put(f'/api/books/{fake_id}',
            data=json.dumps({'title': 'New Title'}),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_update_book_duplicate_isbn(self):
        """Test cập nhật ISBN trùng với sách khác"""
        book1_id = self.create_test_book(isbn='ISBN001')
        book2_id = self.create_test_book(isbn='ISBN002')
        
        response = self.client.put(f'/api/books/{book1_id}',
            data=json.dumps({'isbn': 'ISBN002'}),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 409)
    
    def test_update_book_quantity(self):
        """Test cập nhật quantity"""
        book_id = self.create_test_book(quantity=5, available=5)
        
        response = self.client.put(f'/api/books/{book_id}',
            data=json.dumps({'quantity': 10}),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['data']['quantity'], 10)
        self.assertEqual(data['data']['available'], 10)
    
    def test_update_book_quantity_with_borrowed_copies(self):
        """Test cập nhật quantity khi có sách đang được mượn"""
        book_id = self.create_test_book(quantity=5, available=3)  # 2 copies borrowed
        
        # Không thể giảm quantity xuống dưới số đang mượn
        response = self.client.put(f'/api/books/{book_id}',
            data=json.dumps({'quantity': 1}),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 400)
        
        # Có thể tăng quantity
        response = self.client.put(f'/api/books/{book_id}',
            data=json.dumps({'quantity': 10}),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['data']['quantity'], 10)
        self.assertEqual(data['data']['available'], 8)  # 10 - 2 borrowed
    
    def test_delete_book_success(self):
        """Test xóa sách thành công"""
        book_id = self.create_test_book()
        
        response = self.client.delete(f'/api/books/{book_id}',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify sách đã bị xóa
        response = self.client.get(f'/api/books/{book_id}')
        self.assertEqual(response.status_code, 404)
    
    def test_delete_book_unauthorized(self):
        """Test xóa sách khi chưa đăng nhập"""
        book_id = self.create_test_book()
        
        response = self.client.delete(f'/api/books/{book_id}')
        
        self.assertEqual(response.status_code, 401)
    
    def test_delete_book_not_found(self):
        """Test xóa sách không tồn tại"""
        fake_id = str(ObjectId())
        
        response = self.client.delete(f'/api/books/{fake_id}',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_book_with_borrowed_copies(self):
        """Test xóa sách khi có bản sao đang được mượn"""
        book_id = self.create_test_book(quantity=5, available=4)
        self.create_test_borrow_record(book_id, status='borrowed')
        
        response = self.client.delete(f'/api/books/{book_id}',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 409)
        data = json.loads(response.data)
        self.assertIn('error', data)


# ============================================================
# BORROW RECORDS TESTS
# ============================================================

class TestBorrowRecordsEndpoints(BaseTestCase):
    """Tests cho borrow records endpoints"""
    
    def test_get_borrow_records_empty(self):
        """Test lấy danh sách borrow records khi trống"""
        response = self.client.get('/api/borrow-records',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['records']), 0)
    
    def test_get_borrow_records_unauthorized(self):
        """Test lấy borrow records khi chưa đăng nhập"""
        response = self.client.get('/api/borrow-records')
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_borrow_records_with_data(self):
        """Test lấy danh sách borrow records có dữ liệu"""
        book_id = self.create_test_book()
        self.create_test_borrow_record(book_id)
        self.create_test_borrow_record(book_id)
        
        response = self.client.get('/api/borrow-records',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['data']['records']), 2)
    
    def test_get_borrow_records_filter_by_status(self):
        """Test filter theo status"""
        book_id = self.create_test_book()
        self.create_test_borrow_record(book_id, status='borrowed')
        self.create_test_borrow_record(book_id, status='returned')
        
        response = self.client.get('/api/borrow-records?status=borrowed',
            headers=self.get_auth_headers()
        )
        
        data = json.loads(response.data)
        self.assertEqual(len(data['data']['records']), 1)
        self.assertEqual(data['data']['records'][0]['status'], 'borrowed')
    
    def test_get_borrow_records_filter_by_borrower_name(self):
        """Test filter theo borrower name"""
        book_id = self.create_test_book()
        self.create_test_borrow_record(book_id, borrower_name='John Doe')
        self.create_test_borrow_record(book_id, borrower_name='Jane Smith')
        
        response = self.client.get('/api/borrow-records?borrower_name=John',
            headers=self.get_auth_headers()
        )
        
        data = json.loads(response.data)
        self.assertEqual(len(data['data']['records']), 1)
        self.assertIn('John', data['data']['records'][0]['borrower_name'])
    
    def test_get_borrow_record_by_id(self):
        """Test lấy thông tin một borrow record"""
        book_id = self.create_test_book(title='Test Book')
        record_id = self.create_test_borrow_record(book_id)
        
        response = self.client.get(f'/api/borrow-records/{record_id}',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['id'], record_id)
        self.assertEqual(data['data']['book_title'], 'Test Book')
    
    def test_get_borrow_record_not_found(self):
        """Test lấy borrow record không tồn tại"""
        fake_id = str(ObjectId())
        
        response = self.client.get(f'/api/borrow-records/{fake_id}',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_create_borrow_record_success(self):
        """Test tạo borrow record thành công"""
        book_id = self.create_test_book(quantity=5, available=5)
        
        borrow_data = {
            'book_id': book_id,
            'borrower_name': 'John Doe',
            'borrower_email': 'john@example.com'
        }
        
        response = self.client.post('/api/borrow-records',
            data=json.dumps(borrow_data),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['borrower_name'], 'John Doe')
        self.assertEqual(data['data']['status'], 'borrowed')
        
        # Verify available count decreased
        book = mongo.db.books.find_one({'_id': ObjectId(book_id)})
        self.assertEqual(book['available'], 4)
    
    def test_create_borrow_record_unauthorized(self):
        """Test tạo borrow record khi chưa đăng nhập"""
        book_id = self.create_test_book()
        
        borrow_data = {
            'book_id': book_id,
            'borrower_name': 'John Doe',
            'borrower_email': 'john@example.com'
        }
        
        response = self.client.post('/api/borrow-records',
            data=json.dumps(borrow_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_borrow_record_missing_fields(self):
        """Test tạo borrow record thiếu thông tin"""
        borrow_data = {
            'book_id': str(ObjectId())
            # Missing borrower_name and borrower_email
        }
        
        response = self.client.post('/api/borrow-records',
            data=json.dumps(borrow_data),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_create_borrow_record_book_not_found(self):
        """Test mượn sách không tồn tại"""
        borrow_data = {
            'book_id': str(ObjectId()),
            'borrower_name': 'John Doe',
            'borrower_email': 'john@example.com'
        }
        
        response = self.client.post('/api/borrow-records',
            data=json.dumps(borrow_data),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_create_borrow_record_book_not_available(self):
        """Test mượn sách khi không còn available"""
        book_id = self.create_test_book(quantity=1, available=0)
        
        borrow_data = {
            'book_id': book_id,
            'borrower_name': 'John Doe',
            'borrower_email': 'john@example.com'
        }
        
        response = self.client.post('/api/borrow-records',
            data=json.dumps(borrow_data),
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 409)
    
    def test_return_book_success(self):
        """Test trả sách thành công"""
        book_id = self.create_test_book(quantity=5, available=4)
        record_id = self.create_test_borrow_record(book_id, status='borrowed')
        
        response = self.client.put(f'/api/borrow-records/{record_id}/return',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['status'], 'returned')
        self.assertIsNotNone(data['data']['return_date'])
        
        # Verify available count increased
        book = mongo.db.books.find_one({'_id': ObjectId(book_id)})
        self.assertEqual(book['available'], 5)
    
    def test_return_book_unauthorized(self):
        """Test trả sách khi chưa đăng nhập"""
        book_id = self.create_test_book()
        record_id = self.create_test_borrow_record(book_id)
        
        response = self.client.put(f'/api/borrow-records/{record_id}/return')
        
        self.assertEqual(response.status_code, 401)
    
    def test_return_book_not_found(self):
        """Test trả sách với record không tồn tại"""
        fake_id = str(ObjectId())
        
        response = self.client.put(f'/api/borrow-records/{fake_id}/return',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_return_book_already_returned(self):
        """Test trả sách đã trả rồi"""
        book_id = self.create_test_book()
        record_id = self.create_test_borrow_record(
            book_id,
            status='returned',
            return_date=datetime.utcnow()
        )
        
        response = self.client.put(f'/api/borrow-records/{record_id}/return',
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 409)


# ============================================================
# STATISTICS TESTS
# ============================================================

class TestStatisticsEndpoint(BaseTestCase):
    """Tests cho statistics endpoint"""
    
    def test_statistics_empty_database(self):
        """Test statistics khi database trống"""
        response = self.client.get('/api/statistics')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['books']['total_titles'], 0)
        self.assertEqual(data['data']['books']['total_copies'], 0)
        self.assertEqual(data['data']['borrow_records']['total'], 0)
    
    def test_statistics_with_data(self):
        """Test statistics với dữ liệu"""
        # Tạo books
        book1_id = self.create_test_book(quantity=5, available=5)
        book2_id = self.create_test_book(quantity=3, available=2)
        
        # Tạo borrow records
        self.create_test_borrow_record(book1_id, status='borrowed')
        self.create_test_borrow_record(book2_id, status='borrowed')
        self.create_test_borrow_record(book1_id, status='returned', return_date=datetime.utcnow())
        
        response = self.client.get('/api/statistics')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(data['data']['books']['total_titles'], 2)
        self.assertEqual(data['data']['books']['total_copies'], 8)
        self.assertEqual(data['data']['books']['available_copies'], 7)
        self.assertEqual(data['data']['books']['borrowed_copies'], 2)
        self.assertEqual(data['data']['borrow_records']['total'], 3)
        self.assertEqual(data['data']['borrow_records']['borrowed'], 2)
        self.assertEqual(data['data']['borrow_records']['returned'], 1)


# ============================================================
# HEALTH CHECK TESTS
# ============================================================

class TestHealthCheckEndpoint(BaseTestCase):
    """Tests cho health check endpoint"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/api/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('database', data)


# ============================================================
# CACHE TESTS
# ============================================================

class TestCacheBehavior(BaseTestCase):
    """Tests cho cache behavior"""
    
    def test_cache_headers_on_get_books(self):
        """Test cache headers trên GET /books"""
        response = self.client.get('/api/books')
        
        self.assertIn('Cache-Control', response.headers)
        self.assertIn('public', response.headers['Cache-Control'])
        self.assertIn('ETag', response.headers)
    
    def test_etag_not_modified(self):
        """Test ETag với 304 Not Modified"""
        # First request
        response1 = self.client.get('/api/books')
        etag = response1.headers.get('ETag')
        
        # Second request với If-None-Match
        response2 = self.client.get('/api/books',
            headers={'If-None-Match': etag}
        )
        
        self.assertEqual(response2.status_code, 304)
    
    def test_private_cache_on_authenticated_endpoints(self):
        """Test private cache trên authenticated endpoints"""
        response = self.client.get('/api/auth/verify',
            headers=self.get_auth_headers()
        )
        
        if response.status_code == 200:
            self.assertIn('Cache-Control', response.headers)
            self.assertIn('private', response.headers['Cache-Control'])
    
    def test_no_cache_on_mutations(self):
        """Test no-cache trên mutation operations"""
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'isbn': 'ISBN-TEST',
            'quantity': 5
        }
        
        response = self.client.post('/api/books',
            data=json.dumps(book_data),
            headers=self.get_auth_headers()
        )
        
        if response.status_code == 201:
            self.assertIn('Cache-Control', response.headers)
            self.assertIn('no-store', response.headers['Cache-Control'])


# ============================================================
# ERROR HANDLING TESTS
# ============================================================

class TestErrorHandling(BaseTestCase):
    """Tests cho error handling"""
    
    def test_404_not_found(self):
        """Test 404 error"""
        response = self.client.get('/api/nonexistent')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_405_method_not_allowed(self):
        """Test 405 error"""
        response = self.client.patch('/api/books')
        
        self.assertEqual(response.status_code, 405)
    
    def test_invalid_json(self):
        """Test gửi invalid JSON"""
        response = self.client.post('/api/auth/login',
            data='invalid json',
            content_type='application/json',
            headers=self.get_auth_headers()
        )
        
        # Should handle gracefully
        self.assertIn(response.status_code, [400, 500])


# ============================================================
# ROOT ENDPOINT TEST
# ============================================================

class TestRootEndpoint(BaseTestCase):
    """Tests cho root endpoint"""
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('service', data)
        self.assertIn('version', data)
        self.assertIn('endpoints', data)


if __name__ == '__main__':
    unittest.main()
