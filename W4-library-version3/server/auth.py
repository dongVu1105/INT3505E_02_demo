"""
JWT Authentication Module
Triển khai Stateless Authentication theo nguyên tắc REST
"""
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
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
    
    Nguyên tắc REST - Stateless:
    - Mỗi request PHẢI gửi kèm token trong Authorization header
    - Server KHÔNG lưu trạng thái đăng nhập
    - Token được verify cho MỖI request độc lập
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Lấy token từ Authorization header
        # Standard format: "Bearer <token>"
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                # Tách "Bearer" và token
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1]
                else:
                    return jsonify({
                        'error': 'Invalid Authorization header format',
                        'message': 'Use: Authorization: Bearer <token>'
                    }), 401
            except Exception:
                return jsonify({
                    'error': 'Invalid Authorization header'
                }), 401
        
        if not token:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Token is missing in Authorization header'
            }), 401
        
        # Verify token
        payload = verify_token(token)
        
        if not payload:
            return jsonify({
                'error': 'Authentication failed',
                'message': 'Token is invalid or expired'
            }), 401
        
        # Truyền username vào function
        current_user = payload.get('username')
        
        return f(current_user, *args, **kwargs)
    
    return decorated


def optional_token(f):
    """
    Decorator cho các endpoint có thể truy cập với hoặc không có token
    
    Nếu có token hợp lệ: current_user được truyền vào
    Nếu không có token: current_user = None
    
    Usage:
        @app.route('/public-or-private')
        @optional_token
        def mixed_route(current_user):
            if current_user:
                return jsonify({'message': f'Hello {current_user}'})
            return jsonify({'message': 'Hello Guest'})
    
    Nguyên tắc REST - Stateless:
    - Endpoint linh hoạt xử lý cả authenticated và unauthenticated requests
    - Không lưu state về authentication status
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = None
        
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1]
                    payload = verify_token(token)
                    if payload:
                        current_user = payload.get('username')
            except Exception:
                pass  # Ignore errors, continue as unauthenticated
        
        return f(current_user, *args, **kwargs)
    
    return decorated
