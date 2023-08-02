import os
import pdb

from flask import Flask, abort, flash, g, redirect, render_template, request, session
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import AddGolfRoundForm, AddUserForm, HoleScoreForm, LoginForm
from models import GolfRound, Handicap, HoleScore, User, connect_db, db

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgresql:///golf_tracker"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = True
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)


##########################################################
# User signup/login/logout
@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Handles signing up a user

    Create a new user and add to DB.

    If form NOT valid, present form

    If there is already a user with that username: flash message and re-present form"""

    form = AddUserForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", "danger")
            return render_template("user/signup.html", form=form)

        do_login(user)
        return redirect("/")

    else:
        return render_template("user/signup.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle loggin in a user"""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid Credentials", "danger")

    return render_template("user/login.html", form=form)


@app.route("/logout")
def logout():
    """Handle logout of user."""
    do_logout()

    flash("You have successfully logged out", "success")

    return redirect("/login")


##########################################################


@app.route("/")
def home_page():
    if g.user:
        return render_template("home.html")
    else:
        return render_template("welcome.html")


@app.route("/new_golf_round", methods=["GET", "POST"])
def add_golf_round():
    """Handle User Adding New Golf Round"""
    form = AddGolfRoundForm()

    if form.validate_on_submit():
        # Golf Round Information
        date_played = form.date_played.data
        course_name = form.course_name.data
        hole_count = int(form.hole_count.data)

        # Create Golf Round Instance
        golf_round = GolfRound(
            user_id=g.user.id,
            date_played=date_played,
            course_name=course_name,
            total_score=0,
        )

        # Retrieving data for individual holes from forms
        # Create Each Golf Hole Instance
        for idx in range(hole_count):
            hole_score = HoleScore(
                hole_number=idx + 1,
                fairway_hit=form.hole_scores[idx].fairway_hit.data,
                green_in_regulation=form.hole_scores[idx].green_in_regulation.data,
                putts=form.hole_scores[idx].putts.data,
                score=form.hole_scores[idx].score.data,
            )
            #Add each golf hole to GOLF ROUND
            golf_round.hole_scores.append(hole_score)

            #Update the total score of the golf round
            golf_round.total_score += hole_score.score

            #Add to database
            db.session.add(golf_round)
            db.session.commit()
            

        return redirect("/")

    return render_template("golf_round/new_golf_round.html", form=form)
