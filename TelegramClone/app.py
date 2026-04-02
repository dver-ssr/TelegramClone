from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room, emit
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-in-production!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messenger.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins='*')

# ─── Модели ───────────────────────────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class InviteKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    text = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

# ─── In-memory ────────────────────────────────────────────────────────────────

users = {}  # sid -> username

# ─── HTTP API ─────────────────────────────────────────────────────────────────

@app.route('/generate_invite', methods=['POST'])
def generate_invite():
    data = request.get_json() or {}
    if data.get('admin_key') != 'admin-secret':
        return jsonify({'error': 'Неверный admin_key'}), 403
    key = uuid.uuid4().hex
    db.session.add(InviteKey(key=key))
    db.session.commit()
    return jsonify({'invite_key': key})

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    invite_key = data.get('invite_key', '').strip()

    if not username or not password or not invite_key:
        return jsonify({'error': 'username, password, invite_key обязательны'}), 400

    invite = InviteKey.query.filter_by(key=invite_key, used=False).first()
    if not invite:
        return jsonify({'error': 'Недействительный или использованный ключ'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Имя занято'}), 400

    db.session.add(User(username=username, password_hash=generate_password_hash(password)))
    invite.used = True
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Неверные данные'}), 401
    return jsonify({'status': 'ok', 'username': user.username})

@app.route('/rooms')
def get_rooms():
    rooms = db.session.query(Message.room).distinct().all()
    return jsonify([r[0] for r in rooms])

# ─── Socket.IO Chat ───────────────────────────────────────────────────────────

@socketio.on('join')
def handle_join(data):
    username = data.get('username')
    room = data.get('room')
    if not username or not room:
        return
    if not User.query.filter_by(username=username).first():
        emit('error', {'msg': 'Пользователь не найден'})
        return
    users[request.sid] = username
    join_room(room)
    history = Message.query.filter_by(room=room).order_by(Message.sent_at).limit(50).all()
    emit('history', [{'user': m.username, 'msg': m.text} for m in history])
    emit('status', {'msg': f'{username} вошел в чат.'}, to=room)

@socketio.on('text')
def handle_text(data):
    room = data.get('room')
    msg = data.get('msg', '').strip()
    username = users.get(request.sid)
    if not room or not msg or not username:
        return
    db.session.add(Message(room=room, username=username, text=msg))
    db.session.commit()
    emit('message', {'user': username, 'msg': msg}, to=room)

@socketio.on('leave')
def handle_leave(data):
    room = data.get('room')
    username = users.get(request.sid, 'кто-то')
    leave_room(room)
    emit('status', {'msg': f'{username} покинул чат.'}, to=room)

@socketio.on('disconnect')
def handle_disconnect():
    users.pop(request.sid, None)

# ─── Старт ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print('Сервер запущен: http://0.0.0.0:5000')
    socketio.run(app, host='0.0.0.0', port=5000)
