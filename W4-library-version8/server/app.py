"""
REST API Server
Triển khai kiến trúc Client-Server với Session Authentication

Đặc điểm:
- KHÔNG có template rendering (chỉ trả JSON)
- Sử dụng Flask session để lưu trữ authentication state
- Tách biệt hoàn toàn Server và Client
- CORS enabled với credentials support
"""
from flask import Flask, jsonify, session
from flask_cors import CORS
from flask_session import Session
from models import db
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
    # Cho phép client từ domain khác gọi API với credentials (cookies)
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000", 
                       "http://localhost:5500", "http://127.0.0.1:5500",
                       "http://localhost:8080", "http://127.0.0.1:8080"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True  # Quan trọng: Cho phép gửi cookies
        }
    })
    
    # Initialize server-side session
    Session(app)
    
    # Initialize database
    db.init_app(app)
    
    # Register API blueprint
    app.register_blueprint(api, url_prefix=config_class.API_PREFIX)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
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
        db.session.rollback()
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
║  Architecture: Session-based Client-Server               ║
║  Server running on: http://localhost:{port}                ║
║  API Endpoints: http://localhost:{port}/api                ║
║                                                           ║
║  📚 Đặc điểm:                                            ║
║    ✅ Session-based Authentication                       ║
║    ✅ Client-Server - Tách biệt hoàn toàn               ║
║    ✅ Uniform Interface - HTTP methods chuẩn            ║
║    ✅ Resource-based - URL định danh resources          ║
║    ✅ JSON representation                                ║
║                                                           ║
║  🔐 Authentication: Flask Session (Cookie-based)         ║
║  🍪 Session stored on server-side                        ║
║  📖 Documentation: /openapi.yaml                         ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Run server
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )
