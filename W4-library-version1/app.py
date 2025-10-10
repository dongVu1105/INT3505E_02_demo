from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Book, BorrowRecord
from config import Config
from api_routes import api_bp
from datetime import datetime
import os

# Tạo ứng dụng Flask
app = Flask(__name__)

# Load configuration
app.config.from_object(Config)

# Khởi tạo database
db.init_app(app)

# Đăng ký API Blueprint (RESTful API - Stateless)
app.register_blueprint(api_bp)

# Tạo database và tables
with app.app_context():
    db.create_all()


# ============================================================
# WEB INTERFACE ROUTES
# Giao diện web sử dụng JavaScript để gọi API (Stateless)
# ============================================================

@app.route('/')
def index():
    """
    Trang chủ - Giao diện Single Page Application
    Sử dụng JavaScript để gọi API Stateless
    """
    return render_template('api_index.html')


@app.route('/old')
def old_index():
    """
    Trang chủ cũ (Stateful) - Giữ lại để so sánh
    """
    total_books = Book.query.count()
    available_books = db.session.query(db.func.sum(Book.available)).scalar() or 0
    borrowed_books = BorrowRecord.query.filter_by(status='borrowed').count()
    total_borrows = BorrowRecord.query.count()
    
    return render_template('index.html',
                         total_books=total_books,
                         available_books=available_books,
                         borrowed_books=borrowed_books,
                         total_borrows=total_borrows)


@app.route('/books')
def books():
    """Hiển thị danh sách tất cả sách"""
    all_books = Book.query.order_by(Book.id.desc()).all()
    return render_template('books.html', books=all_books)


@app.route('/books/add', methods=['GET', 'POST'])
def add_book():
    """Thêm sách mới"""
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        quantity = request.form.get('quantity', type=int)
        
        # Kiểm tra ISBN đã tồn tại
        existing_book = Book.query.filter_by(isbn=isbn).first()
        if existing_book:
            flash('ISBN này đã tồn tại trong hệ thống!', 'danger')
            return redirect(url_for('add_book'))
        
        # Tạo sách mới
        new_book = Book(
            title=title,
            author=author,
            isbn=isbn,
            quantity=quantity,
            available=quantity
        )
        
        try:
            db.session.add(new_book)
            db.session.commit()
            flash(f'Đã thêm sách "{title}" thành công!', 'success')
            return redirect(url_for('books'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi thêm sách: {str(e)}', 'danger')
            return redirect(url_for('add_book'))
    
    return render_template('add_book.html')


@app.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    """Chỉnh sửa thông tin sách"""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        new_quantity = request.form.get('quantity', type=int)
        
        # Kiểm tra ISBN trùng với sách khác
        existing_book = Book.query.filter(Book.isbn == isbn, Book.id != book_id).first()
        if existing_book:
            flash('ISBN này đã được sử dụng bởi sách khác!', 'danger')
            return redirect(url_for('edit_book', book_id=book_id))
        
        # Tính toán số lượng available mới
        borrowed_count = book.quantity - book.available
        new_available = new_quantity - borrowed_count
        
        if new_available < 0:
            flash(f'Số lượng sách không đủ! Hiện có {borrowed_count} sách đang được mượn.', 'danger')
            return redirect(url_for('edit_book', book_id=book_id))
        
        # Cập nhật thông tin
        book.title = title
        book.author = author
        book.isbn = isbn
        book.quantity = new_quantity
        book.available = new_available
        
        try:
            db.session.commit()
            flash(f'Đã cập nhật sách "{title}" thành công!', 'success')
            return redirect(url_for('books'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật sách: {str(e)}', 'danger')
    
    return render_template('edit_book.html', book=book)


@app.route('/books/delete/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    """Xóa sách"""
    book = Book.query.get_or_404(book_id)
    
    # Kiểm tra xem có sách đang được mượn không
    borrowed_count = BorrowRecord.query.filter_by(book_id=book_id, status='borrowed').count()
    if borrowed_count > 0:
        flash(f'Không thể xóa! Hiện có {borrowed_count} bản sách đang được mượn.', 'danger')
        return redirect(url_for('books'))
    
    try:
        db.session.delete(book)
        db.session.commit()
        flash(f'Đã xóa sách "{book.title}" thành công!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa sách: {str(e)}', 'danger')
    
    return redirect(url_for('books'))


@app.route('/borrow/<int:book_id>', methods=['GET', 'POST'])
def borrow_book(book_id):
    """Mượn sách"""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        if book.available <= 0:
            flash('Sách này hiện đã hết!', 'danger')
            return redirect(url_for('books'))
        
        borrower_name = request.form.get('borrower_name')
        borrower_email = request.form.get('borrower_email')
        
        # Tạo bản ghi mượn sách
        borrow_record = BorrowRecord(
            book_id=book_id,
            borrower_name=borrower_name,
            borrower_email=borrower_email,
            status='borrowed'
        )
        
        # Giảm số lượng sách available
        book.available -= 1
        
        try:
            db.session.add(borrow_record)
            db.session.commit()
            flash(f'Đã ghi nhận mượn sách "{book.title}" cho {borrower_name}!', 'success')
            return redirect(url_for('borrow_records'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi mượn sách: {str(e)}', 'danger')
    
    return render_template('borrow_book.html', book=book)


@app.route('/return/<int:record_id>', methods=['POST'])
def return_book(record_id):
    """Trả sách"""
    record = BorrowRecord.query.get_or_404(record_id)
    
    if record.status == 'returned':
        flash('Sách này đã được trả rồi!', 'warning')
        return redirect(url_for('borrow_records'))
    
    # Cập nhật trạng thái
    record.status = 'returned'
    record.return_date = datetime.utcnow()
    
    # Tăng số lượng sách available
    book = Book.query.get(record.book_id)
    book.available += 1
    
    try:
        db.session.commit()
        flash(f'Đã xác nhận trả sách "{book.title}"!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi trả sách: {str(e)}', 'danger')
    
    return redirect(url_for('borrow_records'))


@app.route('/borrow-records')
def borrow_records():
    """Hiển thị danh sách mượn/trả sách"""
    status = request.args.get('status', 'all')
    
    if status == 'borrowed':
        records = BorrowRecord.query.filter_by(status='borrowed').order_by(BorrowRecord.borrow_date.desc()).all()
    elif status == 'returned':
        records = BorrowRecord.query.filter_by(status='returned').order_by(BorrowRecord.return_date.desc()).all()
    else:
        records = BorrowRecord.query.order_by(BorrowRecord.borrow_date.desc()).all()
    
    return render_template('borrow_records.html', records=records, status=status)


if __name__ == '__main__':
    app.run(debug=True)
