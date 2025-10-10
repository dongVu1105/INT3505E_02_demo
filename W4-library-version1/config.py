"""
Configuration Module
Quản lý các cấu hình cho ứng dụng
"""
import os
from datetime import timedelta


class Config:
    """
    Cấu hình cơ bản cho ứng dụng
    
    Nguyên tắc Stateless:
    - SECRET_KEY chỉ dùng để ký JWT token, không lưu session
    - Không sử dụng Flask session storage
    """
    
    # Secret key cho JWT token signing
    # QUAN TRỌNG: Thay đổi giá trị này trong production!
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///library.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_EXPIRATION_HOURS = 24  # Token expires after 24 hours
    JWT_ALGORITHM = 'HS256'
    
    # API Configuration
    API_TITLE = 'Library Management API'
    API_VERSION = '2.0.0'
    
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
    
    # Trong production, SECRET_KEY phải được set qua environment variable
    @property
    def SECRET_KEY(self):
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            raise ValueError("SECRET_KEY environment variable must be set in production")
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
