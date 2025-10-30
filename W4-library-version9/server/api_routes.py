"""
REST API Routes
Triển khai đầy đủ REST API theo nguyên tắc Stateless và Cacheable
"""
from flask import Blueprint, request, jsonify, make_response
from models import db, Book, BorrowRecord, get_pagination_params, format_pagination_response
from auth import token_required, optional_token, generate_token
from cache_utils import cacheable, vary_on, invalidate_cache_headers
from datetime import datetime
from sqlalchemy import or_

api = Blueprint('api', __name__)


# ============================================================
# AUTHENTICATION ENDPOINTS
# ============================================================

@api.route('/auth/login', methods=['POST'])
def login():
    """
    POST /api/auth/login
    Đăng nhập và nhận JWT token qua HTTP Cookie
    
    REST Principles:
    - Stateless: Token được tạo và lưu trong cookie, server không lưu session
    - Client-Server: Server chỉ xử lý logic, cookie tự động gửi kèm mỗi request
    - Cacheable: POST request - không cache (sensitive data)
    
    Security:
    - HttpOnly: Cookie không thể truy cập từ JavaScript (phòng chống XSS)
    - Secure: Cookie chỉ gửi qua HTTPS (production)
    - SameSite: Phòng chống CSRF attacks
    """
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({
            'error': 'Bad Request',
            'message': 'Username and password are required'
        }), 400
    
    username = data.get('username')
    password = data.get('password')
    
    # Demo: Chấp nhận bất kỳ username/password nào
    # Trong production, cần verify với database
    # TODO: Implement real authentication with password hashing
    
    token = generate_token(username)
    
    # Non-cacheable response (sensitive data)
    response = make_response(jsonify({
        'success': True,
        'message': 'Login successful',
        'data': {
            'username': username,
            'token_stored': 'cookie'
        }
    }), 200)
    
    # Set JWT token in HTTP-only cookie
    from config import Config
    response.set_cookie(
        'jwt_token',
        token,
        httponly=True,      # Không thể truy cập từ JavaScript
        secure=False,       # Set True trong production với HTTPS
        samesite='Lax',     # Phòng chống CSRF
        max_age=Config.JWT_EXPIRATION_HOURS * 3600
    )
    
    # Explicitly mark as non-cacheable
    for key, value in invalidate_cache_headers().items():
        response.headers[key] = value
    
    return response


@api.route('/auth/logout', methods=['POST'])
def logout():
    """
    POST /api/auth/logout
    Đăng xuất và xóa JWT token cookie
    
    REST Principles:
    - Stateless: Chỉ xóa cookie ở client, server không lưu state
    """
    response = make_response(jsonify({
        'success': True,
        'message': 'Logout successful'
    }), 200)
    
    # Xóa cookie bằng cách set max_age=0
    response.set_cookie(
        'jwt_token',
        '',
        httponly=True,
        secure=False,
        samesite='Lax',
        max_age=0
    )
    
    # Explicitly mark as non-cacheable
    for key, value in invalidate_cache_headers().items():
        response.headers[key] = value
    
    return response


@api.route('/auth/verify', methods=['GET'])
@token_required
@cacheable(cache_type='private', max_age=60, etag_enabled=False)
@vary_on('Authorization')
def verify_token_endpoint(current_user):
    """
    GET /api/auth/verify
    Kiểm tra token có hợp lệ không
    
    REST Principles:
    - Stateless: Verify từ token, không cần tra cứu session
    - Cacheable: Cache ngắn (60s) với private cache (chỉ browser)
    - Vary: Cache phụ thuộc vào Authorization header
    """
    return jsonify({
        'success': True,
        'data': {
            'valid': True,
            'username': current_user
        }
    }), 200


# ============================================================
# BOOKS ENDPOINTS
# ============================================================

@api.route('/books', methods=['GET'])
@cacheable(cache_type='public', max_age=60, etag_enabled=True)
def get_books():
    """
    GET /api/books
    Lấy danh sách sách với pagination và filtering
    
    Query Parameters:
    - page: Số trang (default: 1)
    - per_page: Số items mỗi trang (default: 10, max: 100)
    - author: Filter theo tác giả (partial match)
    - title: Filter theo tiêu đề (partial match)
    - available_only: Chỉ lấy sách còn available (true/false)
    - isbn: Filter theo ISBN (exact match)
    - sort_by: Sắp xếp theo trường (title, author, created_at) (default: created_at)
    - sort_order: Thứ tự sắp xếp (asc, desc) (default: desc)
    
    REST Principles:
    - Stateless: Tất cả filtering qua query params
    - Uniform Interface: Sử dụng HTTP GET method
    - Self-descriptive: Response chứa metadata về pagination
    - Cacheable: Public cache 60s, ETag enabled cho conditional requests
    """
    # Pagination parameters
    page, per_page = get_pagination_params(request, default_per_page=10, max_per_page=100)
    
    # Filtering parameters
    author = request.args.get('author', type=str)
    title = request.args.get('title', type=str)
    isbn = request.args.get('isbn', type=str)
    available_only = request.args.get('available_only', 'false').lower() == 'true'
    
    # Sorting parameters
    sort_by = request.args.get('sort_by', 'created_at', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)
    
    # Build query
    query = Book.query
    
    if author:
        query = query.filter(Book.author.ilike(f'%{author}%'))
    
    if title:
        query = query.filter(Book.title.ilike(f'%{title}%'))
    
    if isbn:
        query = query.filter(Book.isbn == isbn)
    
    if available_only:
        query = query.filter(Book.available > 0)
    
    # Apply sorting
    valid_sort_fields = ['title', 'author', 'created_at', 'isbn']
    if sort_by in valid_sort_fields:
        sort_column = getattr(Book, sort_by)
        if sort_order.lower() == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(Book.created_at.desc())
    
    # Execute with pagination
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Format response using helper function
    response_data = format_pagination_response(pagination, items_key='books')
    
    return jsonify({
        'success': True,
        'data': response_data
    }), 200


@api.route('/books/<int:book_id>', methods=['GET'])
@cacheable(cache_type='public', max_age=120, etag_enabled=True)
def get_book(book_id):
    """
    GET /api/books/{id}
    Lấy thông tin chi tiết một cuốn sách
    
    REST Principles:
    - Stateless: Response chứa đầy đủ thông tin
    - Resource-based: URL định danh resource cụ thể
    - Cacheable: Public cache 120s, ETag enabled
    """
    book = Book.query.get(book_id)
    
    if not book:
        return jsonify({
            'error': 'Not Found',
            'message': f'Book with id {book_id} not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': book.to_dict()
    }), 200


@api.route('/books', methods=['POST'])
@token_required
def create_book(current_user):
    """
    POST /api/books
    Tạo sách mới (yêu cầu authentication)
    
    Request Body:
    {
        "title": "string",
        "author": "string",
        "isbn": "string",
        "quantity": integer
    }
    
    REST Principles:
    - Stateless: Sử dụng JWT token, không session
    - Uniform Interface: POST để tạo resource mới
    - Self-descriptive: Response code 201 Created
    - Cacheable: Không cache (mutation operation)
    """
    data = request.get_json()
    
    # Validation
    required_fields = ['title', 'author', 'isbn', 'quantity']
    if not data or not all(field in data for field in required_fields):
        return jsonify({
            'error': 'Bad Request',
            'message': f'Missing required fields: {", ".join(required_fields)}'
        }), 400
    
    # Validate quantity
    quantity = data.get('quantity', 1)
    if not isinstance(quantity, int) or quantity < 1:
        return jsonify({
            'error': 'Bad Request',
            'message': 'Quantity must be a positive integer'
        }), 400
    
    # Check if ISBN already exists
    existing_book = Book.query.filter_by(isbn=data['isbn']).first()
    if existing_book:
        return jsonify({
            'error': 'Conflict',
            'message': 'A book with this ISBN already exists'
        }), 409
    
    # Create new book
    new_book = Book(
        title=data['title'],
        author=data['author'],
        isbn=data['isbn'],
        quantity=quantity,
        available=quantity
    )
    
    try:
        db.session.add(new_book)
        db.session.commit()
        
        # Non-cacheable response
        response = make_response(jsonify({
            'success': True,
            'message': 'Book created successfully',
            'data': new_book.to_dict()
        }), 201)
        
        for key, value in invalidate_cache_headers().items():
            response.headers[key] = value
        
        return response
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to create book: {str(e)}'
        }), 500


@api.route('/books/<int:book_id>', methods=['PUT'])
@token_required
def update_book(current_user, book_id):
    """
    PUT /api/books/{id}
    Cập nhật thông tin sách (yêu cầu authentication)
    
    REST Principles:
    - Stateless: Request chứa đầy đủ thông tin cần update
    - Idempotent: Gọi nhiều lần với cùng data cho kết quả giống nhau
    - Cacheable: Không cache (mutation operation)
    """
    book = Book.query.get(book_id)
    
    if not book:
        return jsonify({
            'error': 'Not Found',
            'message': f'Book with id {book_id} not found'
        }), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'error': 'Bad Request',
            'message': 'No data provided'
        }), 400
    
    # Check ISBN uniqueness if being changed
    if 'isbn' in data and data['isbn'] != book.isbn:
        existing = Book.query.filter(Book.isbn == data['isbn'], Book.id != book_id).first()
        if existing:
            return jsonify({
                'error': 'Conflict',
                'message': 'ISBN already used by another book'
            }), 409
    
    # Update fields
    if 'title' in data:
        book.title = data['title']
    
    if 'author' in data:
        book.author = data['author']
    
    if 'isbn' in data:
        book.isbn = data['isbn']
    
    # Update quantity - phải kiểm tra số sách đang được mượn
    if 'quantity' in data:
        new_quantity = data['quantity']
        
        if not isinstance(new_quantity, int) or new_quantity < 1:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Quantity must be a positive integer'
            }), 400
        
        borrowed_count = book.quantity - book.available
        new_available = new_quantity - borrowed_count
        
        if new_available < 0:
            return jsonify({
                'error': 'Bad Request',
                'message': f'Cannot reduce quantity. {borrowed_count} copies are currently borrowed'
            }), 400
        
        book.quantity = new_quantity
        book.available = new_available
    
    try:
        db.session.commit()
        
        # Non-cacheable response
        response = make_response(jsonify({
            'success': True,
            'message': 'Book updated successfully',
            'data': book.to_dict()
        }), 200)
        
        for key, value in invalidate_cache_headers().items():
            response.headers[key] = value
        
        return response
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to update book: {str(e)}'
        }), 500


@api.route('/books/<int:book_id>', methods=['DELETE'])
@token_required
def delete_book(current_user, book_id):
    """
    DELETE /api/books/{id}
    Xóa sách (yêu cầu authentication)
    
    REST Principles:
    - Stateless: Chỉ cần ID và token
    - Idempotent: Có thể gọi nhiều lần (lần 2 trở đi trả 404)
    """
    book = Book.query.get(book_id)
    
    if not book:
        return jsonify({
            'error': 'Not Found',
            'message': f'Book with id {book_id} not found'
        }), 404
    
    # Check if any copies are borrowed
    borrowed_count = BorrowRecord.query.filter_by(
        book_id=book_id, 
        status='borrowed'
    ).count()
    
    if borrowed_count > 0:
        return jsonify({
            'error': 'Conflict',
            'message': f'Cannot delete book. {borrowed_count} copies are currently borrowed'
        }), 409
    
    try:
        db.session.delete(book)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Book deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to delete book: {str(e)}'
        }), 500


# ============================================================
# BORROW RECORDS ENDPOINTS
# ============================================================

@api.route('/borrow-records', methods=['GET'])
@token_required
@cacheable(cache_type='private', max_age=30, etag_enabled=True)
@vary_on('Authorization')
def get_borrow_records(current_user):
    """
    GET /api/borrow-records
    Lấy danh sách bản ghi mượn sách
    
    Query Parameters:
    - page: Số trang (default: 1)
    - per_page: Số items mỗi trang (default: 10, max: 100)
    - status: Filter theo status ('borrowed' hoặc 'returned')
    - borrower_name: Filter theo tên người mượn (partial match)
    - borrower_email: Filter theo email người mượn (partial match)
    - book_id: Filter theo ID sách
    - sort_by: Sắp xếp theo trường (borrow_date, return_date, borrower_name) (default: borrow_date)
    - sort_order: Thứ tự sắp xếp (asc, desc) (default: desc)
    
    REST Principles:
    - Stateless: Filtering qua query parameters
    - Cacheable: Private cache 30s (shorter due to frequent changes)
    """
    # Pagination
    page, per_page = get_pagination_params(request, default_per_page=10, max_per_page=100)
    
    # Filtering
    status = request.args.get('status', type=str)
    borrower_name = request.args.get('borrower_name', type=str)
    borrower_email = request.args.get('borrower_email', type=str)
    book_id = request.args.get('book_id', type=int)
    
    # Sorting parameters
    sort_by = request.args.get('sort_by', 'borrow_date', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)
    
    # Build query
    query = BorrowRecord.query
    
    if status in ['borrowed', 'returned']:
        query = query.filter_by(status=status)
    
    if borrower_name:
        query = query.filter(BorrowRecord.borrower_name.ilike(f'%{borrower_name}%'))
    
    if borrower_email:
        query = query.filter(BorrowRecord.borrower_email.ilike(f'%{borrower_email}%'))
    
    if book_id:
        query = query.filter_by(book_id=book_id)
    
    # Apply sorting
    valid_sort_fields = ['borrow_date', 'return_date', 'borrower_name', 'borrower_email', 'status']
    if sort_by in valid_sort_fields:
        sort_column = getattr(BorrowRecord, sort_by)
        if sort_order.lower() == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(BorrowRecord.borrow_date.desc())
    
    # Execute with pagination
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Format response using helper function
    response_data = format_pagination_response(pagination, items_key='records')
    
    return jsonify({
        'success': True,
        'data': response_data
    }), 200


@api.route('/borrow-records/<int:record_id>', methods=['GET'])
@token_required
@cacheable(cache_type='private', max_age=60, etag_enabled=True)
@vary_on('Authorization')
def get_borrow_record(current_user, record_id):
    """
    GET /api/borrow-records/{id}
    Lấy thông tin chi tiết một bản ghi mượn sách
    
    REST Principles:
    - Cacheable: Private cache 60s
    """
    record = BorrowRecord.query.get(record_id)
    
    if not record:
        return jsonify({
            'error': 'Not Found',
            'message': f'Borrow record with id {record_id} not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': record.to_dict()
    }), 200


@api.route('/borrow-records', methods=['POST'])
@token_required
def create_borrow_record(current_user):
    """
    POST /api/borrow-records
    Tạo bản ghi mượn sách mới
    
    Request Body:
    {
        "book_id": integer,
        "borrower_name": "string",
        "borrower_email": "string"
    }
    
    REST Principles:
    - Stateless: Request chứa đầy đủ thông tin
    - Atomic: Transaction đảm bảo consistency
    """
    data = request.get_json()
    
    # Validation
    required_fields = ['book_id', 'borrower_name', 'borrower_email']
    if not data or not all(field in data for field in required_fields):
        return jsonify({
            'error': 'Bad Request',
            'message': f'Missing required fields: {", ".join(required_fields)}'
        }), 400
    
    book_id = data['book_id']
    book = Book.query.get(book_id)
    
    if not book:
        return jsonify({
            'error': 'Not Found',
            'message': f'Book with id {book_id} not found'
        }), 404
    
    if book.available <= 0:
        return jsonify({
            'error': 'Conflict',
            'message': 'Book is not available for borrowing'
        }), 409
    
    # Create borrow record
    borrow_record = BorrowRecord(
        book_id=book_id,
        borrower_name=data['borrower_name'],
        borrower_email=data['borrower_email'],
        status='borrowed'
    )
    
    # Decrease available count
    book.available -= 1
    
    try:
        db.session.add(borrow_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Book borrowed successfully',
            'data': borrow_record.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to create borrow record: {str(e)}'
        }), 500


@api.route('/borrow-records/<int:record_id>/return', methods=['PUT'])
@token_required
def return_book(current_user, record_id):
    """
    PUT /api/borrow-records/{id}/return
    Trả sách
    
    REST Principles:
    - Stateless: Chỉ cần record_id
    - Idempotent: Có thể gọi nhiều lần (lần 2 trở đi trả 409)
    """
    record = BorrowRecord.query.get(record_id)
    
    if not record:
        return jsonify({
            'error': 'Not Found',
            'message': f'Borrow record with id {record_id} not found'
        }), 404
    
    if record.status == 'returned':
        return jsonify({
            'error': 'Conflict',
            'message': 'Book has already been returned'
        }), 409
    
    # Update status
    record.status = 'returned'
    record.return_date = datetime.utcnow()
    
    # Increase available count
    book = Book.query.get(record.book_id)
    if book:
        book.available += 1
    
    try:
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Book returned successfully',
            'data': record.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to return book: {str(e)}'
        }), 500


# ============================================================
# STATISTICS ENDPOINT
# ============================================================

@api.route('/statistics', methods=['GET'])
@cacheable(cache_type='public', max_age=30, etag_enabled=True)
def get_statistics():
    """
    GET /api/statistics
    Lấy thống kê hệ thống
    
    REST Principles:
    - Stateless: Tính toán real-time từ database
    - Cacheable: Public cache 30s (thống kê thay đổi thường xuyên)
    """
    total_books = Book.query.count()
    total_copies = db.session.query(db.func.sum(Book.quantity)).scalar() or 0
    available_copies = db.session.query(db.func.sum(Book.available)).scalar() or 0
    borrowed_copies = BorrowRecord.query.filter_by(status='borrowed').count()
    total_borrow_records = BorrowRecord.query.count()
    returned_records = BorrowRecord.query.filter_by(status='returned').count()
    
    return jsonify({
        'success': True,
        'data': {
            'books': {
                'total_titles': total_books,
                'total_copies': int(total_copies),
                'available_copies': int(available_copies),
                'borrowed_copies': borrowed_copies
            },
            'borrow_records': {
                'total': total_borrow_records,
                'borrowed': borrowed_copies,
                'returned': returned_records
            }
        }
    }), 200


# ============================================================
# HEALTH CHECK ENDPOINT
# ============================================================

@api.route('/health', methods=['GET'])
@cacheable(cache_type='public', max_age=300, etag_enabled=False)
def health_check():
    """
    GET /api/health
    Kiểm tra health của API
    
    REST Principles:
    - Stateless: Không phụ thuộc session hay state
    - Cacheable: Public cache 300s (health status ổn định)
    """
    return jsonify({
        'success': True,
        'status': 'healthy',
        'service': 'Library Management REST API',
        'version': '3.0.0'
    }), 200
