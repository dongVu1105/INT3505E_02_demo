"""
REST API Server
Triển khai kiến trúc Client-Server theo nguyên tắc REST

Đặc điểm:
- KHÔNG có template rendering (chỉ trả JSON)
- KHÔNG có session (Stateless với JWT)
- Tách biệt hoàn toàn Server và Client
- CORS enabled để client từ origin khác có thể gọi
- Sử dụng MongoDB để lưu trữ dữ liệu
"""
from flask import Flask, jsonify
from flask_cors import CORS
from models import mongo
from api_routes import api
from config import Config
import os


def create_app(config_class=Config):
    """
    Application Factory Pattern
    Tạo và cấu hình Flask app
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config_class)
    
    # Enable CORS - Quan trọng cho kiến trúc Client-Server
    # Cho phép client từ domain khác gọi API
    # supports_credentials=True: Cho phép gửi cookies qua CORS
    CORS(app, resources={
        r"/api/v1/*": {
            "origins": app.config['CORS_ORIGINS'],  # Cho phép các origins được cấu hình
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,  # QUAN TRỌNG: Cho phép gửi cookies
            "expose_headers": ["Set-Cookie"]
        }
    })
    
    # Initialize MongoDB
    mongo.init_app(app)
    
    # Register API blueprint
    app.register_blueprint(api, url_prefix=config_class.API_PREFIX)
    
    # Create indexes for MongoDB collections
    with app.app_context():
        try:
            # Test connection first
            mongo.db.command('ping')
            
            # Books collection indexes
            mongo.db.books.create_index('isbn', unique=True)
            mongo.db.books.create_index('title')
            mongo.db.books.create_index('author')
            
            # Borrow records collection indexes
            mongo.db.borrow_records.create_index('book_id')
            mongo.db.borrow_records.create_index('borrower_name')
            mongo.db.borrow_records.create_index('borrower_email')
            mongo.db.borrow_records.create_index('status')
            mongo.db.borrow_records.create_index('borrow_date')
            
            print("✅ MongoDB connection successful and indexes created")
        except Exception as e:
            print(f"⚠️  Warning: Could not connect to MongoDB or create indexes: {e}")
            print("   Please make sure MongoDB is running at the configured URI")
    
    # Root endpoint
    @app.route('/')
    def index():
        """
        Root endpoint - Thông tin về API
        
        REST Principle: Self-descriptive messages
        """
        return jsonify({
            'success': True,
            'service': config_class.API_TITLE,
            'version': config_class.API_VERSION,
            'description': 'REST API Server cho hệ thống quản lý thư viện',
            'architecture': 'Stateless Client-Server REST API',
            'database': 'MongoDB',
            'endpoints': {
                'auth': f'{config_class.API_PREFIX}/auth/login',
                'books': f'{config_class.API_PREFIX}/books',
                'borrow_records': f'{config_class.API_PREFIX}/borrow-records',
                'statistics': f'{config_class.API_PREFIX}/statistics',
                'health': f'{config_class.API_PREFIX}/health'
            },
            'documentation': {
                'openapi': '/openapi.yaml',
                'note': 'Mọi request cần authentication phải gửi kèm: Authorization: Bearer <token>'
            }
        }), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors"""
        return jsonify({
            'error': 'Method Not Allowed',
            'message': 'The method is not allowed for the requested URL'
        }), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
    
    return app


if __name__ == '__main__':
    # Create app
    app = create_app()
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║  🚀 Library Management REST API Server                   ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  Architecture: Stateless Client-Server                   ║
║  Database: MongoDB                                        ║
║  Server running on: http://localhost:{port}                ║
║  API Endpoints: http://localhost:{port}/api/v1             ║
║                                                           ║
║  📚 Nguyên tắc REST được áp dụng:                        ║
║    ✅ Stateless - Không session, dùng JWT               ║
║    ✅ Client-Server - Tách biệt hoàn toàn               ║
║    ✅ Uniform Interface - HTTP methods chuẩn            ║
║    ✅ Resource-based - URL định danh resources          ║
║    ✅ JSON representation                                ║
║                                                           ║
║  🔐 Authentication: JWT Token (Bearer)                   ║
║  📖 Documentation: /openapi.yaml                         ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Run server
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )
