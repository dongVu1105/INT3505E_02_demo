"""
Database Models
Định nghĩa cấu trúc dữ liệu cho REST API với MongoDB
"""
from flask_pymongo import PyMongo
from datetime import datetime
from bson import ObjectId

mongo = PyMongo()


def get_pagination_params(request, default_per_page=10, max_per_page=100):
    """
    Helper function để lấy pagination parameters từ request
    
    Args:
        request: Flask request object
        default_per_page: Số items mặc định mỗi trang
        max_per_page: Số items tối đa mỗi trang
    
    Returns:
        tuple: (page, per_page)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', default_per_page, type=int)
    
    # Validate
    page = max(1, page)  # Trang phải >= 1
    per_page = min(max(1, per_page), max_per_page)  # Giới hạn per_page
    
    return page, per_page


def format_pagination_response(items, total, page, per_page, items_key='items'):
    """
    Helper function để format pagination response
    
    Args:
        items: List of items
        total: Total number of items
        page: Current page
        per_page: Items per page
        items_key: Key name cho items trong response
    
    Returns:
        dict: Formatted response with pagination metadata
    """
    pages = (total + per_page - 1) // per_page  # Ceiling division
    has_next = page < pages
    has_prev = page > 1
    
    return {
        items_key: items,
        'pagination': {
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages,
            'has_next': has_next,
            'has_prev': has_prev,
            'next_page': page + 1 if has_next else None,
            'prev_page': page - 1 if has_prev else None
        }
    }


class Book:
    """
    Model cho sách
    
    Resource representation theo REST principles
    """
    
    @staticmethod
    def to_dict(book_doc):
        """
        Chuyển đổi MongoDB document thành dictionary (JSON-serializable)
        
        REST principle: Resource representation
        """
        if not book_doc:
            return None
            
        return {
            'id': str(book_doc['_id']),
            'title': book_doc.get('title', ''),
            'author': book_doc.get('author', ''),
            'isbn': book_doc.get('isbn', ''),
            'quantity': book_doc.get('quantity', 0),
            'available': book_doc.get('available', 0),
            'created_at': book_doc.get('created_at', datetime.utcnow()).isoformat(),
            'updated_at': book_doc.get('updated_at', datetime.utcnow()).isoformat()
        }
    
    @staticmethod
    def create(title, author, isbn, quantity):
        """Tạo document mới cho sách"""
        return {
            'title': title,
            'author': author,
            'isbn': isbn,
            'quantity': quantity,
            'available': quantity,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }


class BorrowRecord:
    """
    Model cho bản ghi mượn sách
    
    Resource representation theo REST principles
    """
    
    @staticmethod
    def to_dict(record_doc, include_book=True):
        """
        Chuyển đổi MongoDB document thành dictionary (JSON-serializable)
        
        Args:
            record_doc: MongoDB document
            include_book: Có include thông tin sách hay không
        
        REST principle: Resource representation with optional expansion
        """
        if not record_doc:
            return None
            
        result = {
            'id': str(record_doc['_id']),
            'book_id': str(record_doc.get('book_id', '')),
            'borrower_name': record_doc.get('borrower_name', ''),
            'borrower_email': record_doc.get('borrower_email', ''),
            'borrow_date': record_doc.get('borrow_date', datetime.utcnow()).isoformat(),
            'return_date': record_doc.get('return_date').isoformat() if record_doc.get('return_date') else None,
            'status': record_doc.get('status', 'borrowed')
        }
        
        if include_book and record_doc.get('book_title'):
            result['book_title'] = record_doc.get('book_title')
            result['book_author'] = record_doc.get('book_author')
        
        return result
    
    @staticmethod
    def create(book_id, borrower_name, borrower_email):
        """Tạo document mới cho borrow record"""
        return {
            'book_id': ObjectId(book_id),
            'borrower_name': borrower_name,
            'borrower_email': borrower_email,
            'borrow_date': datetime.utcnow(),
            'return_date': None,
            'status': 'borrowed'
        }
