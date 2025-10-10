from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Book(db.Model):
    """Model cho sách"""
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(13), unique=True, nullable=False)
    quantity = db.Column(db.Integer, default=1)  # Số lượng sách có sẵn
    available = db.Column(db.Integer, default=1)  # Số lượng sách còn lại để mượn
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship với BorrowRecord
    borrow_records = db.relationship('BorrowRecord', backref='book', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Book {self.title}>'


class BorrowRecord(db.Model):
    """Model cho bản ghi mượn sách"""
    __tablename__ = 'borrow_records'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    borrower_name = db.Column(db.String(100), nullable=False)
    borrower_email = db.Column(db.String(100), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)  # Null nếu chưa trả
    status = db.Column(db.String(20), default='borrowed')  # 'borrowed' hoặc 'returned'
    
    def __repr__(self):
        return f'<BorrowRecord {self.borrower_name} - {self.book.title}>'
