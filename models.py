from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class GolfRound(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    date_played = db.Column(db.Date, nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    total_score = db.Column(db.Integer, nullable=False)

    # putts_count = db.Column(db.Integer)
    # fairway_hit_count = db.Column(db.Integer)
    # green_hit_count = db.Column(db.Integer)

    hole_scores = db.relationship("HoleScore", backref="golf_round", lazy=True)


class HoleScore(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    golf_round_id = db.Column(
        db.Integer, db.ForeignKey("golf_round.id"), nullable=False
    )
    hole_number = db.Column(db.Integer, nullable=False)
    fairway_hit = db.Column(db.Boolean, nullable=False)
    green_in_regulation = db.Column(db.Boolean, nullable=False)
    putts = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)


class Handicap(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    value = db.Column(db.Float, nullable=False)


def connect_db(app):
    db.app = app
    db.init_app(app)

