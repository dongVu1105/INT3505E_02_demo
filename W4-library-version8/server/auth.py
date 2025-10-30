"""
Session-based Authentication Module
Triển khai Session Authentication với Flask session
"""
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session
from config import Config


def generate_token(username, expires_in=None):
    """
    Tạo JWT token cho user
    
    Args:
        username: Tên người dùng
        expires_in: Thời gian token có hiệu lực (giây). Mặc định lấy từ config
    
    Returns:
        JWT token string
    
    Nguyên tắc REST - Stateless:
    - Token chứa tất cả thông tin cần thiết (username, expiration)
    - Server KHÔNG lưu trữ token
    - Mỗi request mang theo token độc lập
    """
    if expires_in is None:
        expires_in = Config.JWT_EXPIRATION_HOURS * 3600
    
    payload = {
        'username': username,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(
        payload,
        Config.SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM
    )
    
    return token


def verify_token(token):
    """
    Xác thực JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload nếu hợp lệ, None nếu không hợp lệ
    
    Nguyên tắc REST - Stateless:
    - Không tra cứu database hay session store
    - Chỉ verify signature và expiration từ chính token
    - Mỗi request verify token độc lập
    """
    try:
        payload = jwt.decode(
            token,
            Config.SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token đã hết hạn
    except jwt.InvalidTokenError:
        return None  # Token không hợp lệ


def token_required(f):
    """
    Decorator để bảo vệ các endpoint cần authentication
    
    Usage:
        @app.route('/protected')
        @token_required
        def protected_route(current_user):
            return jsonify({'message': f'Hello {current_user}'})
    
    Session-based Authentication:
    - Kiểm tra session để xác thực user
    - Session được lưu trên server và gửi cookie về client
    - Cookie được gửi tự động với mỗi request
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Kiểm tra session có username không
        if 'username' not in session:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please login to access this resource'
            }), 401
        
        current_user = session.get('username')
        
        return f(current_user, *args, **kwargs)
    
    return decorated


def optional_token(f):
    """
    Decorator cho các endpoint có thể truy cập với hoặc không có session
    
    Nếu có session: current_user được truyền vào
    Nếu không có session: current_user = None
    
    Usage:
        @app.route('/public-or-private')
        @optional_token
        def mixed_route(current_user):
            if current_user:
                return jsonify({'message': f'Hello {current_user}'})
            return jsonify({'message': 'Hello Guest'})
    
    Session-based Authentication:
    - Endpoint linh hoạt xử lý cả authenticated và unauthenticated requests
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = session.get('username', None)
        
        return f(current_user, *args, **kwargs)
    
    return decorated
