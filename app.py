from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from peewee import Model, IntegerField, DateTimeField, CharField, SqliteDatabase, SQL
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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
    user_id = CharField(unique=True)  # Unique identifier for each user
    last_visit = DateTimeField()

# Create the tables if they don't exist
with app.app_context():
    db.connect()
    db.create_tables([ViewCount, User], safe=True)

@app.route('/increment', methods=['POST'])
def increment_views():
    try:
        user_id = request.cookies.get('user_id')  # Retrieve user ID from cookies
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
            # Update or create user record
            user, created = User.get_or_create(user_id=user_id)
            user.last_visit = now
            user.save()
        else:
            # Create a new user record
            user_id = str(now.timestamp())  # Use timestamp as a unique identifier
            user = User.create(user_id=user_id, last_visit=now)
            resp = make_response(jsonify({"message": "View count incremented", "views": view_count_today.count}))
            resp.set_cookie('user_id', user_id)  # Set cookie with the user ID
            return resp

        return jsonify({"message": "View count incremented", "views": view_count_today.count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/count')
def get_count():
    try:
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/unique_users')
def get_unique_users():
    try:
        # Retrieve all unique users
        users = User.select()
        return jsonify({"unique_users": len(users)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/online')
def get_online_count():
    try:
        # Placeholder for online count; implement tracking for real use
        return jsonify({"online_count": 0})  # Placeholder value
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Default to 5000 if PORT is not set
    app.run(host='0.0.0.0', port=port, debug=True)
