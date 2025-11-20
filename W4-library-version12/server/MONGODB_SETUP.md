# MongoDB Setup cho Testing

## Yêu cầu

Tests cần MongoDB đang chạy để hoạt động đúng. Có nhiều cách để setup MongoDB:

## Option 1: MongoDB Local Installation (Khuyến nghị)

### Windows
1. Download MongoDB Community Server từ: https://www.mongodb.com/try/download/community
2. Cài đặt với default settings
3. MongoDB sẽ chạy như một Windows Service

### Khởi động MongoDB Service
```powershell
# Kiểm tra status
net start | findstr MongoDB

# Start MongoDB service
net start MongoDB

# Stop MongoDB service
net stop MongoDB
```

### Verify MongoDB đang chạy
```powershell
# Sử dụng MongoDB Shell
mongosh mongodb://localhost:27017

# Hoặc kiểm tra với Python
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017'); print('MongoDB connected:', client.admin.command('ping'))"
```

## Option 2: Docker (Đơn giản nhất)

### Cài đặt Docker Desktop
1. Download từ: https://www.docker.com/products/docker-desktop
2. Cài đặt và khởi động Docker Desktop

### Chạy MongoDB trong Docker
```bash
# Pull và run MongoDB
docker run -d \
  --name mongodb-test \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=root \
  -e MONGO_INITDB_ROOT_PASSWORD=root \
  mongo:latest

# Verify container đang chạy
docker ps | findstr mongodb-test

# Stop container
docker stop mongodb-test

# Start lại container
docker start mongodb-test

# Xóa container
docker rm -f mongodb-test
```

### Windows PowerShell
```powershell
# Run MongoDB
docker run -d --name mongodb-test -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=root mongo:latest

# Verify
docker ps

# Xem logs
docker logs mongodb-test
```

## Option 3: MongoDB Atlas (Cloud)

### Sử dụng Free Tier
1. Tạo account tại: https://www.mongodb.com/cloud/atlas/register
2. Tạo free cluster (M0 Sandbox - 512MB)
3. Whitelist IP address (hoặc allow từ anywhere: 0.0.0.0/0)
4. Tạo database user
5. Lấy connection string

### Cập nhật connection string
```python
# Trong test_api.py, cập nhật TestConfig
class TestConfig(Config):
    MONGO_URI = 'mongodb+srv://username:password@cluster.mongodb.net/library-test?retryWrites=true&w=majority'
```

## Cấu hình Connection String

### Default (Local MongoDB)
```python
MONGO_URI = 'mongodb://localhost:27017/library-test'
```

### With Authentication
```python
MONGO_URI = 'mongodb://root:root@localhost:27017/library-test?authSource=admin'
```

### Docker
```python
MONGO_URI = 'mongodb://root:root@localhost:27017/library-test?authSource=admin'
```

### MongoDB Atlas
```python
MONGO_URI = 'mongodb+srv://username:password@cluster.mongodb.net/library-test?retryWrites=true&w=majority'
```

## Test Database

Tests sử dụng database riêng: `library-test`

- ✅ Tách biệt khỏi production database
- ✅ Tự động cleanup sau mỗi test
- ✅ An toàn để drop và recreate

### Manual Cleanup
```python
from pymongo import MongoClient

# Connect
client = MongoClient('mongodb://root:root@localhost:27017')

# Drop test database
client.drop_database('library-test')

# Verify
print('Databases:', client.list_database_names())
```

## Troubleshooting

### Error: Connection refused (WinError 10061)
**Nguyên nhân**: MongoDB không chạy

**Giải pháp**:
```powershell
# Check MongoDB service
net start MongoDB

# Hoặc start Docker container
docker start mongodb-test
```

### Error: Authentication failed
**Nguyên nhân**: Username/password không đúng

**Giải pháp**: Cập nhật connection string trong `TestConfig`

### Error: Timeout connecting to MongoDB
**Nguyên nhân**: Firewall hoặc network issue

**Giải pháp**:
1. Check firewall settings
2. Verify MongoDB port (27017) không bị block
3. Thử connect với `mongodb://127.0.0.1:27017` thay vì `localhost`

### Error: Database operation failed
**Nguyên nhân**: Database permissions

**Giải pháp**:
1. Ensure user có write permissions
2. Check `authSource` trong connection string

## Verify Setup

### Test Connection Script
Tạo file `test_mongodb_connection.py`:

```python
from pymongo import MongoClient
import sys

def test_connection(uri):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        
        # Test ping
        client.admin.command('ping')
        print('✅ MongoDB connected successfully!')
        
        # List databases
        dbs = client.list_database_names()
        print(f'✅ Available databases: {dbs}')
        
        # Test write
        test_db = client['library-test']
        test_db.test_collection.insert_one({'test': 'data'})
        print('✅ Write operation successful!')
        
        # Test read
        doc = test_db.test_collection.find_one({'test': 'data'})
        print(f'✅ Read operation successful! Document: {doc}')
        
        # Cleanup
        test_db.test_collection.delete_many({})
        print('✅ Cleanup successful!')
        
        client.close()
        return True
        
    except Exception as e:
        print(f'❌ MongoDB connection failed: {e}')
        return False

if __name__ == '__main__':
    uri = 'mongodb://root:root@localhost:27017/library-test?authSource=admin'
    
    if len(sys.argv) > 1:
        uri = sys.argv[1]
    
    print(f'Testing connection to: {uri}')
    success = test_connection(uri)
    sys.exit(0 if success else 1)
```

### Run Test
```bash
python test_mongodb_connection.py
```

## Recommended Setup for Development

### 1. Use Docker for consistency
```bash
# Start MongoDB
docker run -d --name mongodb-dev -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=root mongo:latest
```

### 2. Create helper script
Tạo `start_mongodb.bat`:
```batch
@echo off
docker start mongodb-dev 2>nul || docker run -d --name mongodb-dev -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=root mongo:latest
echo MongoDB started!
```

### 3. Add to your workflow
```bash
# Before running tests
start_mongodb.bat

# Run tests
python -m unittest test_api.py

# Optionally stop MongoDB
docker stop mongodb-dev
```

## CI/CD Setup

### GitHub Actions Example
```yaml
services:
  mongodb:
    image: mongo:latest
    ports:
      - 27017:27017
    env:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: root
```

### GitLab CI Example
```yaml
services:
  - mongo:latest

variables:
  MONGO_INITDB_ROOT_USERNAME: root
  MONGO_INITDB_ROOT_PASSWORD: root
```

## Best Practices

1. ✅ Use separate database for testing (`library-test`)
2. ✅ Auto cleanup after tests
3. ✅ Use Docker for portability
4. ✅ Document connection requirements
5. ✅ Provide setup scripts
6. ✅ Test MongoDB connection before running tests
