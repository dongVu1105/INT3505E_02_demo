"""
Script để test MongoDB connection trước khi chạy tests
"""
from pymongo import MongoClient
import sys

def test_connection(uri):
    """Test MongoDB connection"""
    try:
        print(f'Testing connection to: {uri}')
        print('-' * 60)
        
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        
        # Test ping
        result = client.admin.command('ping')
        print('✅ MongoDB ping successful!')
        
        # List databases
        dbs = client.list_database_names()
        print(f'✅ Available databases: {dbs}')
        
        # Test write to test database
        test_db = client['library-test']
        test_result = test_db.test_collection.insert_one({'test': 'data', 'timestamp': 'now'})
        print(f'✅ Write operation successful! Inserted ID: {test_result.inserted_id}')
        
        # Test read
        doc = test_db.test_collection.find_one({'test': 'data'})
        print(f'✅ Read operation successful! Document: {doc}')
        
        # Count documents
        count = test_db.test_collection.count_documents({})
        print(f'✅ Count operation successful! Documents: {count}')
        
        # Cleanup
        delete_result = test_db.test_collection.delete_many({})
        print(f'✅ Cleanup successful! Deleted {delete_result.deleted_count} documents')
        
        # Test indexes
        test_db.books.create_index('isbn', unique=True)
        print('✅ Index creation successful!')
        
        client.close()
        
        print('-' * 60)
        print('✅ All MongoDB operations successful!')
        print('✅ You can now run the tests!')
        return True
        
    except Exception as e:
        print('-' * 60)
        print(f'❌ MongoDB connection failed!')
        print(f'Error: {e}')
        print('')
        print('Troubleshooting:')
        print('1. Make sure MongoDB is running')
        print('   Windows: net start MongoDB')
        print('   Docker: docker start mongodb-dev')
        print('2. Check connection string')
        print('3. Verify username/password')
        print('4. Check firewall settings')
        return False


if __name__ == '__main__':
    # Default URI
    uri = 'mongodb://root:root@localhost:27017/library-test?authSource=admin'
    
    # Allow custom URI from command line
    if len(sys.argv) > 1:
        uri = sys.argv[1]
    
    print('')
    print('=' * 60)
    print('  MongoDB Connection Test')
    print('=' * 60)
    print('')
    
    success = test_connection(uri)
    
    print('')
    sys.exit(0 if success else 1)
