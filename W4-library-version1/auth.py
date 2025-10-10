"""
JWT Authentication Module
Thực hiện Stateless Authentication theo nguyên tắc REST
"""
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from config import Config


def generate_token(username, expires_in=3600):
    """
    Tạo JWT token cho user
    
    Args:
        username: Tên người dùng
        expires_in: Thời gian token có hiệu lực (giây), mặc định 1 giờ
    
    Returns:
        JWT token string
    
    Nguyên tắc Stateless:
    - Token chứa tất cả thông tin cần thiết (username, expiration)
    - Server không lưu trữ token, chỉ verify signature
    - Mỗi request mang theo token riêng, độc lập
    """
    payload = {
        'username': username,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(
        payload,
        Config.SECRET_KEY,
        algorithm='HS256'
    )
    
    return token


def verify_token(token):
    """
    Xác thực JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload nếu hợp lệ, None nếu không hợp lệ
    
    Nguyên tắc Stateless:
    - Không cần tra cứu database hoặc session store
    - Chỉ verify signature và expiration từ token
    """
    try:
        payload = jwt.decode(
            token,
            Config.SECRET_KEY,
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token đã hết hạn
    except jwt.InvalidTokenError:
        return None  # Token không hợp lệ


def token_required(f):
    """
    Decorator để bảo vệ các endpoint cần authentication
    
    Sử dụng:
        @app.route('/protected')
        @token_required
        def protected_route(current_user):
            return jsonify({'message': f'Hello {current_user}'})
    
    Nguyên tắc Stateless:
    - Mỗi request phải gửi kèm token trong header
    - Server không lưu trạng thái đăng nhập
    - Token được verify cho mỗi request
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Lấy token từ Authorization header
        # Format: "Bearer <token>"
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                # Tách "Bearer" và token
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format. Use: Bearer <token>'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        # Verify token
        payload = verify_token(token)
        
        if not payload:
            return jsonify({'error': 'Token is invalid or expired'}), 401
        
        # Truyền username vào function
        current_user = payload.get('username')
        
        return f(current_user, *args, **kwargs)
    
    return decorated


def optional_token(f):
    """
    Decorator cho các endpoint có thể access với hoặc không có token
    
    Nếu có token hợp lệ, current_user sẽ được truyền vào
    Nếu không có token hoặc token không hợp lệ, current_user = None
    
    Nguyên tắc Stateless:
    - Endpoint linh hoạt, có thể xử lý cả authenticated và unauthenticated requests
    - Không lưu state về việc user đã từng login hay chưa
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        current_user = None
        
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token = auth_header.split(" ")[1]
                payload = verify_token(token)
                if payload:
                    current_user = payload.get('username')
            except (IndexError, Exception):
                pass  # Ignore errors, continue as unauthenticated
        
        return f(current_user, *args, **kwargs)
    
    return decorated
