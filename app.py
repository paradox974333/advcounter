from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from peewee import Model, IntegerField, DateTimeField, CharField, SqliteDatabase, SQL
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

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

@app.route('/increment', methods=['POST'])
def increment_views():
    try:
        user_id = request.cookies.get('user_id')
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        
        view_count_today, created = ViewCount.get_or_create(date=today_start)
        view_count_today.count += 1
        view_count_today.save()

        if user_id:
            user, created = User.get_or_create(user_id=user_id)
        else:
            user_id = str(now.timestamp())
            user = User.create(user_id=user_id)

        user.last_visit = now
        user.save()

        resp = make_response(jsonify({"message": "View count incremented", "views": view_count_today.count}))
        resp.set_cookie('user_id', user_id, max_age=365*24*60*60)  # Set cookie for 1 year
        return resp

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/count')
def get_count():
    try:
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        yesterday_start = today_start - timedelta(days=1)
        
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
        unique_users = User.select().count()
        return jsonify({"unique_users": unique_users})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/online')
def get_online_count():
    try:
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        online_count = User.select().where(User.last_visit >= five_minutes_ago).count()
        return jsonify({"online_count": online_count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
