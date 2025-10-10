"""
RESTful API Routes - Tuân thủ nguyên tắc Stateless
Sử dụng JWT cho authentication thay vì session
"""
from flask import Blueprint, request, jsonify
from models import db, Book, BorrowRecord
from auth import token_required, generate_token
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api')


# ============== Authentication Endpoints ==============

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """
    Đăng nhập và nhận JWT token
    Stateless: Không lưu session trên server
    """
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    # Demo: accept any username/password, trong thực tế cần verify với database
    username = data.get('username')
    password = data.get('password')
    
    # Tạo JWT token
    token = generate_token(username)
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'username': username
    }), 200


# ============== Books Endpoints ==============

@api_bp.route('/books', methods=['GET'])
def get_books():
    """
    Lấy danh sách tất cả sách
    Stateless: Mỗi request độc lập, không phụ thuộc session
    """
    # Query parameters cho filtering và pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    author = request.args.get('author', type=str)
    available_only = request.args.get('available_only', 'false').lower() == 'true'
    
    # Build query
    query = Book.query
    
    if author:
        query = query.filter(Book.author.ilike(f'%{author}%'))
    
    if available_only:
        query = query.filter(Book.available > 0)
    
    # Pagination
    pagination = query.order_by(Book.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    books = [{
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'isbn': book.isbn,
        'quantity': book.quantity,
        'available': book.available,
        'created_at': book.created_at.isoformat()
    } for book in pagination.items]
    
    return jsonify({
        'books': books,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'per_page': per_page
    }), 200


@api_bp.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """
    Lấy thông tin chi tiết một cuốn sách
    Stateless: Response chứa đầy đủ thông tin, không cần state từ request trước
    """
    book = Book.query.get(book_id)
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify({
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'isbn': book.isbn,
        'quantity': book.quantity,
        'available': book.available,
        'created_at': book.created_at.isoformat()
    }), 200


@api_bp.route('/books', methods=['POST'])
@token_required
def create_book(current_user):
    """
    Thêm sách mới (yêu cầu authentication)
    Stateless: Sử dụng JWT token trong header, không dùng session
    """
    data = request.get_json()
    
    # Validation
    if not data or not all(k in data for k in ['title', 'author', 'isbn', 'quantity']):
        return jsonify({'error': 'Missing required fields: title, author, isbn, quantity'}), 400
    
    # Kiểm tra ISBN đã tồn tại
    existing_book = Book.query.filter_by(isbn=data['isbn']).first()
    if existing_book:
        return jsonify({'error': 'ISBN already exists'}), 409
    
    # Validate quantity
    quantity = data.get('quantity', 1)
    if quantity < 1:
        return jsonify({'error': 'Quantity must be at least 1'}), 400
    
    # Tạo sách mới
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
        
        return jsonify({
            'message': 'Book created successfully',
            'book': {
                'id': new_book.id,
                'title': new_book.title,
                'author': new_book.author,
                'isbn': new_book.isbn,
                'quantity': new_book.quantity,
                'available': new_book.available,
                'created_at': new_book.created_at.isoformat()
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create book: {str(e)}'}), 500


@api_bp.route('/books/<int:book_id>', methods=['PUT'])
@token_required
def update_book(current_user, book_id):
    """
    Cập nhật thông tin sách (yêu cầu authentication)
    Stateless: Request chứa đầy đủ thông tin cần update
    """
    book = Book.query.get(book_id)
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Kiểm tra ISBN trùng với sách khác
    if 'isbn' in data and data['isbn'] != book.isbn:
        existing_book = Book.query.filter(Book.isbn == data['isbn'], Book.id != book_id).first()
        if existing_book:
            return jsonify({'error': 'ISBN already used by another book'}), 409
    
    # Update fields
    if 'title' in data:
        book.title = data['title']
    if 'author' in data:
        book.author = data['author']
    if 'isbn' in data:
        book.isbn = data['isbn']
    
    # Update quantity - cần kiểm tra số sách đang được mượn
    if 'quantity' in data:
        new_quantity = data['quantity']
        borrowed_count = book.quantity - book.available
        new_available = new_quantity - borrowed_count
        
        if new_available < 0:
            return jsonify({
                'error': f'Invalid quantity. {borrowed_count} books are currently borrowed'
            }), 400
        
        book.quantity = new_quantity
        book.available = new_available
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Book updated successfully',
            'book': {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'isbn': book.isbn,
                'quantity': book.quantity,
                'available': book.available,
                'created_at': book.created_at.isoformat()
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update book: {str(e)}'}), 500


@api_bp.route('/books/<int:book_id>', methods=['DELETE'])
@token_required
def delete_book(current_user, book_id):
    """
    Xóa sách (yêu cầu authentication)
    Stateless: Mỗi request độc lập
    """
    book = Book.query.get(book_id)
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    # Kiểm tra sách đang được mượn
    borrowed_count = BorrowRecord.query.filter_by(book_id=book_id, status='borrowed').count()
    if borrowed_count > 0:
        return jsonify({
            'error': f'Cannot delete book. {borrowed_count} copies are currently borrowed'
        }), 409
    
    try:
        db.session.delete(book)
        db.session.commit()
        
        return jsonify({'message': 'Book deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete book: {str(e)}'}), 500


# ============== Borrow Records Endpoints ==============

@api_bp.route('/borrow-records', methods=['GET'])
@token_required
def get_borrow_records(current_user):
    """
    Lấy danh sách bản ghi mượn sách
    Stateless: Filtering qua query parameters, không lưu state
    """
    # Query parameters
    status = request.args.get('status', type=str)  # 'borrowed' or 'returned'
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Build query
    query = BorrowRecord.query
    
    if status in ['borrowed', 'returned']:
        query = query.filter_by(status=status)
    
    # Pagination
    pagination = query.order_by(BorrowRecord.borrow_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    records = [{
        'id': record.id,
        'book_id': record.book_id,
        'book_title': record.book.title,
        'borrower_name': record.borrower_name,
        'borrower_email': record.borrower_email,
        'borrow_date': record.borrow_date.isoformat(),
        'return_date': record.return_date.isoformat() if record.return_date else None,
        'status': record.status
    } for record in pagination.items]
    
    return jsonify({
        'records': records,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'per_page': per_page
    }), 200


@api_bp.route('/borrow-records/<int:record_id>', methods=['GET'])
@token_required
def get_borrow_record(current_user, record_id):
    """
    Lấy thông tin chi tiết một bản ghi mượn sách
    Stateless: Response đầy đủ thông tin
    """
    record = BorrowRecord.query.get(record_id)
    
    if not record:
        return jsonify({'error': 'Borrow record not found'}), 404
    
    return jsonify({
        'id': record.id,
        'book_id': record.book_id,
        'book_title': record.book.title,
        'borrower_name': record.borrower_name,
        'borrower_email': record.borrower_email,
        'borrow_date': record.borrow_date.isoformat(),
        'return_date': record.return_date.isoformat() if record.return_date else None,
        'status': record.status
    }), 200


@api_bp.route('/borrow-records', methods=['POST'])
@token_required
def create_borrow_record(current_user):
    """
    Tạo bản ghi mượn sách mới
    Stateless: Request chứa đầy đủ thông tin cần thiết
    """
    data = request.get_json()
    
    # Validation
    if not data or not all(k in data for k in ['book_id', 'borrower_name', 'borrower_email']):
        return jsonify({
            'error': 'Missing required fields: book_id, borrower_name, borrower_email'
        }), 400
    
    book_id = data['book_id']
    book = Book.query.get(book_id)
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    if book.available <= 0:
        return jsonify({'error': 'Book is not available'}), 409
    
    # Tạo bản ghi mượn sách
    borrow_record = BorrowRecord(
        book_id=book_id,
        borrower_name=data['borrower_name'],
        borrower_email=data['borrower_email'],
        status='borrowed'
    )
    
    # Giảm số lượng sách available
    book.available -= 1
    
    try:
        db.session.add(borrow_record)
        db.session.commit()
        
        return jsonify({
            'message': 'Book borrowed successfully',
            'record': {
                'id': borrow_record.id,
                'book_id': borrow_record.book_id,
                'book_title': book.title,
                'borrower_name': borrow_record.borrower_name,
                'borrower_email': borrow_record.borrower_email,
                'borrow_date': borrow_record.borrow_date.isoformat(),
                'status': borrow_record.status
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create borrow record: {str(e)}'}), 500


@api_bp.route('/borrow-records/<int:record_id>/return', methods=['PUT'])
@token_required
def return_book(current_user, record_id):
    """
    Trả sách (cập nhật bản ghi mượn sách)
    Stateless: Chỉ cần record_id, không cần thông tin từ request trước
    """
    record = BorrowRecord.query.get(record_id)
    
    if not record:
        return jsonify({'error': 'Borrow record not found'}), 404
    
    if record.status == 'returned':
        return jsonify({'error': 'Book already returned'}), 409
    
    # Cập nhật trạng thái
    record.status = 'returned'
    record.return_date = datetime.utcnow()
    
    # Tăng số lượng sách available
    book = Book.query.get(record.book_id)
    book.available += 1
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Book returned successfully',
            'record': {
                'id': record.id,
                'book_id': record.book_id,
                'book_title': book.title,
                'borrower_name': record.borrower_name,
                'borrower_email': record.borrower_email,
                'borrow_date': record.borrow_date.isoformat(),
                'return_date': record.return_date.isoformat(),
                'status': record.status
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to return book: {str(e)}'}), 500


# ============== Statistics Endpoint ==============

@api_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """
    Lấy thống kê hệ thống
    Stateless: Tính toán dựa trên database hiện tại, không lưu cache
    """
    total_books = Book.query.count()
    available_books = db.session.query(db.func.sum(Book.available)).scalar() or 0
    borrowed_books = BorrowRecord.query.filter_by(status='borrowed').count()
    total_borrows = BorrowRecord.query.count()
    
    return jsonify({
        'total_books': total_books,
        'available_books': int(available_books),
        'borrowed_books': borrowed_books,
        'total_borrows': total_borrows
    }), 200
