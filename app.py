from flask import Flask, jsonify, request, make_response, send_from_directory
from flask_cors import CORS
from peewee import Model, IntegerField, DateTimeField, CharField, SqliteDatabase, SQL
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)
app.secret_key = 'your_secret_key'

# Configure the database
db = SqliteDatabase('views.db')

class BaseModel(Model):
    class Meta:
        database = db

class ViewCount(BaseModel):
    count = IntegerField(default=0)
    date = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])
    online_count = IntegerField(default=0)

class User(BaseModel):
    user_id = CharField(unique=True)
    last_visit = DateTimeField()

with app.app_context():
    db.connect()
    db.create_tables([ViewCount, User], safe=True)

# In-memory dictionary to track online users
online_users = {}

@app.route('/increment', methods=['POST'])
def increment_views():
    global online_users
    user_id = request.cookies.get('user_id')
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    yesterday_start = today_start - timedelta(days=1)

    # Update today's count
    view_count_today, created = ViewCount.get_or_create(date=today_start)
    view_count_today.count += 1
    view_count_today.save()

    # Reset yesterday's count
    view_count_yesterday = ViewCount.select().where(ViewCount.date == yesterday_start).first()
    if view_count_yesterday:
        view_count_yesterday.count = 0
        view_count_yesterday.save()

    if user_id:
        user, created = User.get_or_create(user_id=user_id)
        user.last_visit = now
        user.save()
        online_users[user_id] = now
        print(f"Existing user {user_id} updated. Online users: {online_users}")
    else:
        user_id = str(now.timestamp())
        user = User.create(user_id=user_id, last_visit=now)
        online_users[user_id] = now
        resp = make_response(jsonify({"message": "View count incremented", "views": view_count_today.count}))
        resp.set_cookie('user_id', user_id)
        print(f"New user created: {user_id}. Online users: {online_users}")
        return resp

    return jsonify({"message": "View count incremented", "views": view_count_today.count})

@app.route('/count', methods=['GET'])
def get_count():
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    yesterday_start = today_start - timedelta(days=1)

    # Retrieve counts
    view_count_today = ViewCount.select().where(ViewCount.date == today_start).first()
    view_count_yesterday = ViewCount.select().where(ViewCount.date == yesterday_start).first()

    return jsonify({
        "today": view_count_today.count if view_count_today else 0,
        "yesterday": view_count_yesterday.count if view_count_yesterday else 0
    })

@app.route('/unique_users', methods=['GET'])
def get_unique_users():
    # Retrieve all unique users
    users = User.select()
    return jsonify({"unique_users": len(users)})

@app.route('/online', methods=['GET'])
def get_online_count():
    expiry_time = datetime.now() - timedelta(minutes=5)
    global online_users
    online_users = {uid: last_seen for uid, last_seen in online_users.items() if last_seen > expiry_time}
    print(f"Online users after expiry check: {online_users}")
    return jsonify({"online_count": len(online_users)})

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
