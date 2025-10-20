"""
Cache Utilities Module
Triển khai Cacheable Principle của REST Architecture

Nguyên tắc Cacheable:
- Response phải được đánh dấu rõ ràng là cacheable hay non-cacheable
- Sử dụng HTTP cache headers: Cache-Control, ETag, Last-Modified
- Hỗ trợ conditional requests để tối ưu bandwidth
"""
import hashlib
import json
from flask import request, make_response
from functools import wraps
from datetime import datetime, timedelta


def generate_etag(data):
    """
    Tạo ETag từ data
    
    ETag (Entity Tag) là một identifier cho một version cụ thể của resource.
    Client có thể gửi If-None-Match header với ETag để kiểm tra xem
    resource có thay đổi không.
    
    Args:
        data: Dict hoặc list để tạo ETag
    
    Returns:
        str: ETag value (MD5 hash của data)
    """
    if isinstance(data, (dict, list)):
        content = json.dumps(data, sort_keys=True)
    else:
        content = str(data)
    
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def add_cache_headers(response, cache_type='public', max_age=300):
    """
    Thêm cache headers vào response
    
    Cache-Control directives:
    - public: Response có thể cache bởi browser và proxy
    - private: Chỉ cache bởi browser (không cache ở proxy)
    - no-cache: Phải revalidate với server trước khi sử dụng
    - no-store: Không cache (dùng cho sensitive data)
    - max-age: Thời gian cache tính bằng giây
    
    Args:
        response: Flask response object
        cache_type: Loại cache ('public', 'private', 'no-cache', 'no-store')
        max_age: Thời gian cache (giây)
    
    Returns:
        response: Response với cache headers
    """
    if cache_type == 'no-store':
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif cache_type == 'no-cache':
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
    else:
        response.headers['Cache-Control'] = f'{cache_type}, max-age={max_age}'
        
        # Thêm Expires header cho backward compatibility
        expires = datetime.utcnow() + timedelta(seconds=max_age)
        response.headers['Expires'] = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    return response


def cacheable(cache_type='public', max_age=300, etag_enabled=True):
    """
    Decorator để thêm cache support cho endpoint
    
    Features:
    - Tự động thêm Cache-Control headers
    - Tự động tạo và kiểm tra ETag
    - Xử lý conditional requests (304 Not Modified)
    - Thêm Last-Modified header
    
    Args:
        cache_type: Loại cache ('public', 'private', 'no-cache', 'no-store')
        max_age: Thời gian cache (giây)
        etag_enabled: Có sử dụng ETag không
    
    Usage:
        @api.route('/resource')
        @cacheable(cache_type='public', max_age=300)
        def get_resource():
            return jsonify({'data': 'value'})
    
    REST Principle - Cacheable:
    - Response được đánh dấu rõ ràng về cacheability
    - Hỗ trợ conditional requests để tiết kiệm bandwidth
    - Server và client cùng tối ưu hiệu năng
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Gọi function gốc
            result = f(*args, **kwargs)
            
            # Tạo response object
            if isinstance(result, tuple):
                response_data, status_code = result[0], result[1]
                response = make_response(response_data, status_code)
            else:
                response = make_response(result)
            
            # Chỉ cache cho GET requests và success responses (2xx)
            if request.method != 'GET' or response.status_code >= 300:
                # Non-cacheable responses
                return add_cache_headers(response, 'no-store', 0)
            
            # Thêm Last-Modified header
            response.headers['Last-Modified'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            # ETag support
            if etag_enabled:
                try:
                    # Lấy response data để tạo ETag
                    response_json = response.get_json()
                    if response_json:
                        etag = generate_etag(response_json)
                        response.headers['ETag'] = f'"{etag}"'
                        
                        # Kiểm tra If-None-Match header (conditional request)
                        if_none_match = request.headers.get('If-None-Match')
                        if if_none_match:
                            # Remove quotes nếu có
                            client_etag = if_none_match.strip('"')
                            if client_etag == etag:
                                # Resource không thay đổi - trả 304 Not Modified
                                response = make_response('', 304)
                                response.headers['ETag'] = f'"{etag}"'
                                return add_cache_headers(response, cache_type, max_age)
                except:
                    # Nếu không parse được JSON, bỏ qua ETag
                    pass
            
            # Thêm cache headers
            return add_cache_headers(response, cache_type, max_age)
        
        return decorated_function
    return decorator


def vary_on(headers):
    """
    Thêm Vary header để chỉ định cache phải xem xét headers nào
    
    Vary header cho cache biết là cache phải lưu trữ các version khác nhau
    của response dựa trên giá trị của headers được chỉ định.
    
    Args:
        headers: List of header names hoặc single header name
    
    Example:
        @vary_on(['Authorization', 'Accept-Language'])
        def endpoint():
            ...
    
    REST Principle - Cacheable:
    - Cache có thể vary theo context (user, language, etc.)
    """
    if isinstance(headers, str):
        headers = [headers]
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            
            if isinstance(result, tuple):
                response = make_response(result[0], result[1])
            else:
                response = make_response(result)
            
            # Thêm Vary header
            response.headers['Vary'] = ', '.join(headers)
            
            return response
        
        return decorated_function
    return decorator


def invalidate_cache_headers():
    """
    Tạo headers để invalidate cache
    Dùng cho các mutation operations (POST, PUT, DELETE)
    
    Returns:
        dict: Headers để thêm vào response
    """
    return {
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0'
    }


def get_cache_status(response):
    """
    Lấy thông tin về cache status từ response
    Dùng cho debugging và monitoring
    
    Args:
        response: Flask response object
    
    Returns:
        dict: Cache status info
    """
    return {
        'cache_control': response.headers.get('Cache-Control'),
        'etag': response.headers.get('ETag'),
        'last_modified': response.headers.get('Last-Modified'),
        'expires': response.headers.get('Expires'),
        'vary': response.headers.get('Vary')
    }
