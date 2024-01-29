import os
DB_PASSWORD = os.environ.get('DB_PASSWORD', '12345')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_NAME = "postgres"
DB_HOST = "localhost"
DB_PORT = "9000"
REDIS_HOST = "localhost"
REDIS_PORT = 6379

DB_CONFIG = {
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'port': DB_PORT
}
MONGO_URI = "mongodb://localhost:27017/chat_app"
