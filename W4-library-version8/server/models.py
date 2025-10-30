"""
Database Models
Định nghĩa cấu trúc dữ liệu cho REST API
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


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


def format_pagination_response(pagination, items_key='items'):
    """
    Helper function để format pagination response
    
    Args:
        pagination: SQLAlchemy pagination object
        items_key: Key name cho items trong response
    
    Returns:
        dict: Formatted response with pagination metadata
    """
    return {
        items_key: [item.to_dict() for item in pagination.items],
        'pagination': {
            'total': pagination.total,
            'page': pagination.page,
            'per_page': pagination.per_page,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'next_page': pagination.page + 1 if pagination.has_next else None,
            'prev_page': pagination.page - 1 if pagination.has_prev else None
        }
    }


class Book(db.Model):
    """
    Model cho sách
    
    Resource representation theo REST principles
    """
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    author = db.Column(db.String(100), nullable=False, index=True)
    isbn = db.Column(db.String(13), unique=True, nullable=False, index=True)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    available = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    borrow_records = db.relationship('BorrowRecord', backref='book', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """
        Chuyển đổi object thành dictionary (JSON-serializable)
        
        REST principle: Resource representation
        """
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'quantity': self.quantity,
            'available': self.available,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Book {self.title}>'


class BorrowRecord(db.Model):
    """
    Model cho bản ghi mượn sách
    
    Resource representation theo REST principles
    """
    __tablename__ = 'borrow_records'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, index=True)
    borrower_name = db.Column(db.String(100), nullable=False, index=True)
    borrower_email = db.Column(db.String(100), nullable=False, index=True)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='borrowed', index=True)  # 'borrowed' hoặc 'returned'
    
    def to_dict(self, include_book=True):
        """
        Chuyển đổi object thành dictionary (JSON-serializable)
        
        Args:
            include_book: Có include thông tin sách hay không
        
        REST principle: Resource representation with optional expansion
        """
        result = {
            'id': self.id,
            'book_id': self.book_id,
            'borrower_name': self.borrower_name,
            'borrower_email': self.borrower_email,
            'borrow_date': self.borrow_date.isoformat(),
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'status': self.status
        }
        
        if include_book and self.book:
            result['book_title'] = self.book.title
            result['book_author'] = self.book.author
        
        return result
    
    def __repr__(self):
        return f'<BorrowRecord {self.borrower_name} - {self.book.title if self.book else "Unknown"}>'
