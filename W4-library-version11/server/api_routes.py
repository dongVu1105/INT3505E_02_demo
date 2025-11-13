"""
REST API Routes với MongoDB
Triển khai đầy đủ REST API theo nguyên tắc Stateless và Cacheable
"""
from flask import Blueprint, request, jsonify, make_response
from models import mongo, Book, BorrowRecord, get_pagination_params, format_pagination_response
from auth import token_required, optional_token, generate_token
from cache_utils import cacheable, vary_on, invalidate_cache_headers
from datetime import datetime
from bson import ObjectId
import re

api = Blueprint('api', __name__)


# ============================================================
# AUTHENTICATION ENDPOINTS
# ============================================================

@api.route('/auth/login', methods=['POST'])
def login():
    """
    POST /api/auth/login
    Đăng nhập và nhận JWT token qua HTTP Cookie
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
    token = generate_token(username)
    
    response = make_response(jsonify({
        'success': True,
        'message': 'Login successful',
        'data': {
            'username': username,
            'token_stored': 'cookie'
        }
    }), 200)
    
    from config import Config
    response.set_cookie(
        'jwt_token',
        token,
        httponly=True,
        secure=False,
        samesite='Lax',
        max_age=Config.JWT_EXPIRATION_HOURS * 3600
    )
    
    for key, value in invalidate_cache_headers().items():
        response.headers[key] = value
    
    return response


@api.route('/auth/logout', methods=['POST'])
def logout():
    """POST /api/auth/logout - Đăng xuất"""
    response = make_response(jsonify({
        'success': True,
        'message': 'Logout successful'
    }), 200)
    
    response.set_cookie(
        'jwt_token',
        '',
        httponly=True,
        secure=False,
        samesite='Lax',
        max_age=0
    )
    
    for key, value in invalidate_cache_headers().items():
        response.headers[key] = value
    
    return response


@api.route('/auth/verify', methods=['GET'])
@token_required
@cacheable(cache_type='private', max_age=60, etag_enabled=False)
@vary_on('Authorization')
def verify_token_endpoint(current_user):
    """GET /api/auth/verify - Kiểm tra token"""
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
    query = {}
    
    if author:
        query['author'] = {'$regex': author, '$options': 'i'}
    
    if title:
        query['title'] = {'$regex': title, '$options': 'i'}
    
    if isbn:
        query['isbn'] = isbn
    
    if available_only:
        query['available'] = {'$gt': 0}
    
    # Apply sorting
    valid_sort_fields = ['title', 'author', 'created_at', 'isbn']
    if sort_by in valid_sort_fields:
        sort_direction = 1 if sort_order.lower() == 'asc' else -1
        sort_spec = [(sort_by, sort_direction)]
    else:
        sort_spec = [('created_at', -1)]
    
    # Count total
    total = mongo.db.books.count_documents(query)
    
    # Execute with pagination
    skip = (page - 1) * per_page
    books_cursor = mongo.db.books.find(query).sort(sort_spec).skip(skip).limit(per_page)
    
    # Convert to list of dicts
    books = [Book.to_dict(book) for book in books_cursor]
    
    # Format response
    response_data = format_pagination_response(books, total, page, per_page, items_key='books')
    
    return jsonify({
        'success': True,
        'data': response_data
    }), 200


@api.route('/books/<book_id>', methods=['GET'])
@cacheable(cache_type='public', max_age=120, etag_enabled=True)
def get_book(book_id):
    """GET /api/books/{id} - Lấy thông tin chi tiết một cuốn sách"""
    try:
        book = mongo.db.books.find_one({'_id': ObjectId(book_id)})
    except:
        return jsonify({
            'error': 'Bad Request',
            'message': 'Invalid book ID format'
        }), 400
    
    if not book:
        return jsonify({
            'error': 'Not Found',
            'message': f'Book with id {book_id} not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': Book.to_dict(book)
    }), 200


@api.route('/books', methods=['POST'])
@token_required
def create_book(current_user):
    """POST /api/books - Tạo sách mới"""
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
    existing_book = mongo.db.books.find_one({'isbn': data['isbn']})
    if existing_book:
        return jsonify({
            'error': 'Conflict',
            'message': 'A book with this ISBN already exists'
        }), 409
    
    # Create new book
    new_book = Book.create(
        title=data['title'],
        author=data['author'],
        isbn=data['isbn'],
        quantity=quantity
    )
    
    try:
        result = mongo.db.books.insert_one(new_book)
        new_book['_id'] = result.inserted_id
        
        response = make_response(jsonify({
            'success': True,
            'message': 'Book created successfully',
            'data': Book.to_dict(new_book)
        }), 201)
        
        for key, value in invalidate_cache_headers().items():
            response.headers[key] = value
        
        return response
        
    except Exception as e:
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to create book: {str(e)}'
        }), 500


@api.route('/books/<book_id>', methods=['PUT'])
@token_required
def update_book(current_user, book_id):
    """PUT /api/books/{id} - Cập nhật thông tin sách"""
    try:
        book = mongo.db.books.find_one({'_id': ObjectId(book_id)})
    except:
        return jsonify({
            'error': 'Bad Request',
            'message': 'Invalid book ID format'
        }), 400
    
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
    if 'isbn' in data and data['isbn'] != book['isbn']:
        existing = mongo.db.books.find_one({
            'isbn': data['isbn'],
            '_id': {'$ne': ObjectId(book_id)}
        })
        if existing:
            return jsonify({
                'error': 'Conflict',
                'message': 'ISBN already used by another book'
            }), 409
    
    # Prepare update
    update_fields = {}
    
    if 'title' in data:
        update_fields['title'] = data['title']
    
    if 'author' in data:
        update_fields['author'] = data['author']
    
    if 'isbn' in data:
        update_fields['isbn'] = data['isbn']
    
    # Update quantity - phải kiểm tra số sách đang được mượn
    if 'quantity' in data:
        new_quantity = data['quantity']
        
        if not isinstance(new_quantity, int) or new_quantity < 1:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Quantity must be a positive integer'
            }), 400
        
        borrowed_count = book['quantity'] - book['available']
        new_available = new_quantity - borrowed_count
        
        if new_available < 0:
            return jsonify({
                'error': 'Bad Request',
                'message': f'Cannot reduce quantity. {borrowed_count} copies are currently borrowed'
            }), 400
        
        update_fields['quantity'] = new_quantity
        update_fields['available'] = new_available
    
    update_fields['updated_at'] = datetime.utcnow()
    
    try:
        mongo.db.books.update_one(
            {'_id': ObjectId(book_id)},
            {'$set': update_fields}
        )
        
        # Get updated book
        updated_book = mongo.db.books.find_one({'_id': ObjectId(book_id)})
        
        response = make_response(jsonify({
            'success': True,
            'message': 'Book updated successfully',
            'data': Book.to_dict(updated_book)
        }), 200)
        
        for key, value in invalidate_cache_headers().items():
            response.headers[key] = value
        
        return response
        
    except Exception as e:
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to update book: {str(e)}'
        }), 500


@api.route('/books/<book_id>', methods=['DELETE'])
@token_required
def delete_book(current_user, book_id):
    """DELETE /api/books/{id} - Xóa sách"""
    try:
        book = mongo.db.books.find_one({'_id': ObjectId(book_id)})
    except:
        return jsonify({
            'error': 'Bad Request',
            'message': 'Invalid book ID format'
        }), 400
    
    if not book:
        return jsonify({
            'error': 'Not Found',
            'message': f'Book with id {book_id} not found'
        }), 404
    
    # Check if any copies are borrowed
    borrowed_count = mongo.db.borrow_records.count_documents({
        'book_id': ObjectId(book_id),
        'status': 'borrowed'
    })
    
    if borrowed_count > 0:
        return jsonify({
            'error': 'Conflict',
            'message': f'Cannot delete book. {borrowed_count} copies are currently borrowed'
        }), 409
    
    try:
        # Delete all related borrow records first
        mongo.db.borrow_records.delete_many({'book_id': ObjectId(book_id)})
        # Delete the book
        mongo.db.books.delete_one({'_id': ObjectId(book_id)})
        
        return jsonify({
            'success': True,
            'message': 'Book deleted successfully'
        }), 200
        
    except Exception as e:
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
    """GET /api/borrow-records - Lấy danh sách bản ghi mượn sách"""
    # Pagination
    page, per_page = get_pagination_params(request, default_per_page=10, max_per_page=100)
    
    # Filtering
    status = request.args.get('status', type=str)
    borrower_name = request.args.get('borrower_name', type=str)
    borrower_email = request.args.get('borrower_email', type=str)
    book_id = request.args.get('book_id', type=str)
    
    # Sorting parameters
    sort_by = request.args.get('sort_by', 'borrow_date', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)
    
    # Build query
    query = {}
    
    if status in ['borrowed', 'returned']:
        query['status'] = status
    
    if borrower_name:
        query['borrower_name'] = {'$regex': borrower_name, '$options': 'i'}
    
    if borrower_email:
        query['borrower_email'] = {'$regex': borrower_email, '$options': 'i'}
    
    if book_id:
        try:
            query['book_id'] = ObjectId(book_id)
        except:
            pass
    
    # Apply sorting
    valid_sort_fields = ['borrow_date', 'return_date', 'borrower_name', 'borrower_email', 'status']
    if sort_by in valid_sort_fields:
        sort_direction = 1 if sort_order.lower() == 'asc' else -1
        sort_spec = [(sort_by, sort_direction)]
    else:
        sort_spec = [('borrow_date', -1)]
    
    # Count total
    total = mongo.db.borrow_records.count_documents(query)
    
    # Execute with pagination
    skip = (page - 1) * per_page
    records_cursor = mongo.db.borrow_records.find(query).sort(sort_spec).skip(skip).limit(per_page)
    
    # Convert to list of dicts with book info
    records = []
    for record in records_cursor:
        # Get book info
        book = mongo.db.books.find_one({'_id': record['book_id']})
        if book:
            record['book_title'] = book['title']
            record['book_author'] = book['author']
        records.append(BorrowRecord.to_dict(record))
    
    # Format response
    response_data = format_pagination_response(records, total, page, per_page, items_key='records')
    
    return jsonify({
        'success': True,
        'data': response_data
    }), 200


@api.route('/borrow-records/<record_id>', methods=['GET'])
@token_required
@cacheable(cache_type='private', max_age=60, etag_enabled=True)
@vary_on('Authorization')
def get_borrow_record(current_user, record_id):
    """GET /api/borrow-records/{id} - Lấy thông tin chi tiết một bản ghi mượn sách"""
    try:
        record = mongo.db.borrow_records.find_one({'_id': ObjectId(record_id)})
    except:
        return jsonify({
            'error': 'Bad Request',
            'message': 'Invalid record ID format'
        }), 400
    
    if not record:
        return jsonify({
            'error': 'Not Found',
            'message': f'Borrow record with id {record_id} not found'
        }), 404
    
    # Get book info
    book = mongo.db.books.find_one({'_id': record['book_id']})
    if book:
        record['book_title'] = book['title']
        record['book_author'] = book['author']
    
    return jsonify({
        'success': True,
        'data': BorrowRecord.to_dict(record)
    }), 200


@api.route('/borrow-records', methods=['POST'])
@token_required
def create_borrow_record(current_user):
    """POST /api/borrow-records - Tạo bản ghi mượn sách mới"""
    data = request.get_json()
    
    # Validation
    required_fields = ['book_id', 'borrower_name', 'borrower_email']
    if not data or not all(field in data for field in required_fields):
        return jsonify({
            'error': 'Bad Request',
            'message': f'Missing required fields: {", ".join(required_fields)}'
        }), 400
    
    book_id = data['book_id']
    
    try:
        book = mongo.db.books.find_one({'_id': ObjectId(book_id)})
    except:
        return jsonify({
            'error': 'Bad Request',
            'message': 'Invalid book ID format'
        }), 400
    
    if not book:
        return jsonify({
            'error': 'Not Found',
            'message': f'Book with id {book_id} not found'
        }), 404
    
    if book['available'] <= 0:
        return jsonify({
            'error': 'Conflict',
            'message': 'Book is not available for borrowing'
        }), 409
    
    # Create borrow record
    borrow_record = BorrowRecord.create(
        book_id=book_id,
        borrower_name=data['borrower_name'],
        borrower_email=data['borrower_email']
    )
    
    try:
        # Insert record
        result = mongo.db.borrow_records.insert_one(borrow_record)
        borrow_record['_id'] = result.inserted_id
        
        # Decrease available count
        mongo.db.books.update_one(
            {'_id': ObjectId(book_id)},
            {'$inc': {'available': -1}}
        )
        
        # Add book info to record
        borrow_record['book_title'] = book['title']
        borrow_record['book_author'] = book['author']
        
        return jsonify({
            'success': True,
            'message': 'Book borrowed successfully',
            'data': BorrowRecord.to_dict(borrow_record)
        }), 201
        
    except Exception as e:
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to create borrow record: {str(e)}'
        }), 500


@api.route('/borrow-records/<record_id>/return', methods=['PUT'])
@token_required
def return_book(current_user, record_id):
    """PUT /api/borrow-records/{id}/return - Trả sách"""
    try:
        record = mongo.db.borrow_records.find_one({'_id': ObjectId(record_id)})
    except:
        return jsonify({
            'error': 'Bad Request',
            'message': 'Invalid record ID format'
        }), 400
    
    if not record:
        return jsonify({
            'error': 'Not Found',
            'message': f'Borrow record with id {record_id} not found'
        }), 404
    
    if record['status'] == 'returned':
        return jsonify({
            'error': 'Conflict',
            'message': 'Book has already been returned'
        }), 409
    
    try:
        # Update status
        mongo.db.borrow_records.update_one(
            {'_id': ObjectId(record_id)},
            {
                '$set': {
                    'status': 'returned',
                    'return_date': datetime.utcnow()
                }
            }
        )
        
        # Increase available count
        mongo.db.books.update_one(
            {'_id': record['book_id']},
            {'$inc': {'available': 1}}
        )
        
        # Get updated record
        updated_record = mongo.db.borrow_records.find_one({'_id': ObjectId(record_id)})
        book = mongo.db.books.find_one({'_id': updated_record['book_id']})
        if book:
            updated_record['book_title'] = book['title']
            updated_record['book_author'] = book['author']
        
        return jsonify({
            'success': True,
            'message': 'Book returned successfully',
            'data': BorrowRecord.to_dict(updated_record)
        }), 200
        
    except Exception as e:
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
    """GET /api/statistics - Lấy thống kê hệ thống"""
    total_books = mongo.db.books.count_documents({})
    
    # Calculate total copies and available copies using aggregation
    pipeline = [
        {
            '$group': {
                '_id': None,
                'total_copies': {'$sum': '$quantity'},
                'available_copies': {'$sum': '$available'}
            }
        }
    ]
    
    result = list(mongo.db.books.aggregate(pipeline))
    
    if result:
        total_copies = result[0]['total_copies']
        available_copies = result[0]['available_copies']
    else:
        total_copies = 0
        available_copies = 0
    
    borrowed_copies = mongo.db.borrow_records.count_documents({'status': 'borrowed'})
    total_borrow_records = mongo.db.borrow_records.count_documents({})
    returned_records = mongo.db.borrow_records.count_documents({'status': 'returned'})
    
    return jsonify({
        'success': True,
        'data': {
            'books': {
                'total_titles': total_books,
                'total_copies': total_copies,
                'available_copies': available_copies,
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
    """GET /api/health - Kiểm tra health của API"""
    try:
        # Test MongoDB connection
        mongo.db.command('ping')
        db_status = 'connected'
    except:
        db_status = 'disconnected'
    
    return jsonify({
        'success': True,
        'status': 'healthy',
        'service': 'Library Management REST API',
        'version': '3.0.0',
        'database': {
            'type': 'MongoDB',
            'status': db_status
        }
    }), 200
