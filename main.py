from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import psycopg2
from psycopg2 import sql
from pymongo import MongoClient
from datetime import datetime
from utils import DB_CONFIG, REDIS_HOST, REDIS_PORT, MONGO_URI
import redis

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app)

def connect_to_redis():
    return redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

client = MongoClient(MONGO_URI)
db = client["chat_app"]
message_collection = db["messages"]

def create_or_get_room(user1, user2):
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cursor:
        # Check if a room already exists for these users
        cursor.execute(sql.SQL("""
            SELECT id FROM room
            WHERE (user1 = %s AND user2 = %s) OR (user1 = %s AND user2 = %s);
        """), (user1, user2, user2, user1))
        existing_room = cursor.fetchone()

        if existing_room:
            return existing_room[0]

        room_id = str(uuid.uuid4())
        cursor.execute(sql.SQL("""
            INSERT INTO room (id, user1, user2) VALUES (%s, %s, %s);
        """), (room_id, user1, user2))
        conn.commit()
        return room_id


@socketio.on('connect')
def connect():
    print(f"user connected")

@socketio.on('disconnect')
def disconnect():
    print(f"user disconnected")

@socketio.on('join_room')
def handle_join_room(data):
    username = data['username']
    partner_username = data['partner_username']
    room_id = create_or_get_room(username, partner_username)
    join_room(room_id)
    emit('joined_room', {'username': username, 'room': room_id}, room=room_id)
    print(f'{username} joined room {room_id}')


@socketio.on('leave_room')
def handle_leave_room(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    emit('left_room', {'username': username, 'room': room}, room=room)
    print(f'{username} left room {room}')

@socketio.on('message')
def send_message(data):
    sender_username = data['sender']
    recipient_username = data['receiver']
    room_id = create_or_get_room(sender_username, recipient_username)
    print(room_id)
    message_content = data['content']
    print(message_content)
    timestamp = datetime.utcnow()
    message_data = {
        'room_id': room_id,
        'sender': sender_username,
        'receiver': recipient_username,
        'message': message_content,
        'timestamp':timestamp
    }
    result = message_collection.insert_one(message_data)
    print(f"Message Inserted: {result.inserted_id}")
    emit('message', {'sender': sender_username, 'message': message_content}, room=room_id)

from flask import request

def fetch_messages(page):
    start_index = (page - 1) * 2
    end_index = start_index + 2
    return message_collection[start_index:end_index]

@app.route('/chat_history', methods=["GET"])
def chat_history():
    username = request.args.get('username')
    partner_username=request.args.get('partner_username')
    room_id = request.args.get('room_id')
    page = int(request.args.get('page', 1))
    redis_conn = connect_to_redis()
    redis_conn.set("username", datetime.utcnow().timestamp())
    redis_conn.set("partner_username", datetime.utcnow().timestamp())
    read_username=redis_conn.get("username")
    read_partner_username=redis_conn.get("partner_username")
    print(read_username)
    print(read_partner_username)
    if not username or not room_id:
        return jsonify({"error": "Username and room_id are required parameters"}), 400

    messages_per_page = 2

    skip = (page - 1) * messages_per_page

    chat_history = message_collection.find({"room_id": room_id}).sort("timestamp", 1).skip(skip).limit(messages_per_page)
    
    messages = [{"message": message["message"], "sender": message["sender"], "receiver": message["receiver"], "timestamp": str(message["timestamp"])}
                for message in chat_history]

    total_messages = message_collection.count_documents({"room_id": room_id})
    total_pages = (total_messages // messages_per_page) + 1

    return render_template('history.html', username=username, partner_username=partner_username, room_id=room_id, messages=messages, total_pages=total_pages,read_username=read_username,read_partner_username=read_partner_username)


if __name__ == '__main__':
    socketio.run(app, debug=True)
