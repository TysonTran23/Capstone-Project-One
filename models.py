from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()


class User(db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    
    # ... methods ...


    @classmethod
    def signup(cls, username, email, password):
        """
        Sign up user

        Hashes password and adds user to system.

        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode("UTF-8")

        user = User(username=username, email=email, password=hashed_pwd)

        db.session.add(user)

        return user

    @classmethod
    def authenticate(cls, username, password):
        """
        Find user with 'username' and 'password'
        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """
        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user
        
        return False

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"


class GolfRound(db.Model):

    __tablename__ = "golf_rounds"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date_played = db.Column(db.Date, nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    par = db.Column(db.Integer, nullable=False)
    total_score = db.Column(db.Integer, nullable=False)

    # putts_count = db.Column(db.Integer)
    # fairway_hit_count = db.Column(db.Integer)
    # green_hit_count = db.Column(db.Integer)

    hole_scores = db.relationship("HoleScore", backref="golf_round", lazy=True)

    def __repr__(self):
        return f"<User #{self.user_id} Date: {self.date_played} Course: {self.course_name} Total Score: {self.total_score}>"


class HoleScore(db.Model):

    __tablename__ = "holes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    golf_round_id = db.Column(
        db.Integer, db.ForeignKey("golf_rounds.id"), nullable=False
    )
    hole_number = db.Column(db.Integer, nullable=False)
    par = db.Column(db.Integer, nullable=False)
    fairway_hit = db.Column(db.Boolean, nullable=False)
    green_in_regulation = db.Column(db.Boolean, nullable=False)
    putts = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Hole: {self.hole_number} Hit Fairway: {self.fairway_hit} Hit Green: {self.green_in_regulation} Putts: {self.putts} Score: {self.score}>"


class Handicap(db.Model):

    __tablename__ = "handicaps"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    value = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<User #{self.user_id} Handicap: {self.value}>"

def connect_db(app):
    db.app = app
    db.init_app(app)
