"""
Configuration Module for REST API Server
Quản lý cấu hình theo nguyên tắc Stateless
"""
import os
from datetime import timedelta


class Config:
    """
    Cấu hình cơ bản cho REST API Server
    
    Nguyên tắc REST - Stateless:
    - Không sử dụng Flask session
    - SECRET_KEY chỉ để ký JWT token
    - Không lưu trữ state trên server
    """
    
    # Secret key cho JWT token signing
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///library.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_EXPIRATION_HOURS = 24  # Token hết hạn sau 24 giờ
    JWT_ALGORITHM = 'HS256'
    
    # CORS Configuration - Cho phép client từ origin khác
    # Bao gồm nhiều port phổ biến và null cho file:// protocol
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8080,http://127.0.0.1:8080,null').split(',')
    
    # API Configuration
    API_TITLE = 'Library Management REST API'
    API_VERSION = '3.0.0'
    API_PREFIX = '/api'
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100


class DevelopmentConfig(Config):
    """Cấu hình cho môi trường development"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Cấu hình cho môi trường production"""
    DEBUG = False
    TESTING = False
    
    @property
    def SECRET_KEY(self):
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            raise ValueError("SECRET_KEY must be set in production")
        return secret_key


class TestingConfig(Config):
    """Cấu hình cho môi trường testing"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_library.db'


# Config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
