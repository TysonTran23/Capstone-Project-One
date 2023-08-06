import os
import pdb
import time

import requests
from flask import Flask, abort, flash, g, redirect, render_template, request, session
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import (
    AddGolfRoundForm,
    AddGolfRoundForm18,
    AddUserForm,
    HoleScoreForm,
    LoginForm,
)
from models import GolfRound, Handicap, HoleScore, User, connect_db, db

CURR_USER_KEY = "curr_user"
BASE_URL = "https:api.sportsdata.io/golf/v2/json"
URL_KEY = "key=176964ab9ddb48dea44c9fb38e4adbc8"


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


####################################################################################################################
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
        # Authenticate User
        user = User.authenticate(form.username.data, form.password.data)

        # If authentication successful, login
        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        # If NOT, Flash error message
        flash("Invalid Credentials", "danger")

    return render_template("user/login.html", form=form)


@app.route("/logout")
def logout():
    """Handle logout of user."""
    do_logout()

    flash("You have successfully logged out", "success")

    return redirect("/login")


####################################################################################################################


@app.route("/")
def home_page():
    if g.user:
        return render_template("home.html")
    else:
        return render_template("welcome.html")


####################################################################################################################
# Standalone Functions for Golf Rounds
def create_golf_round(user_id, date_played, course_name):
    """Create a GolfRound Instace and save it to database"""
    golf_round = GolfRound(
        user_id=user_id,
        date_played=date_played,
        course_name=course_name,
        par=0,
        total_score=0,
    )
    db.session.add(golf_round)
    db.session.commit()

    return golf_round


def save_hole_scores(golf_round, hole_scores_form, hole_count):
    """Save hole scores to the database for the given golf round"""
    for idx in range(hole_count):
        hole_score = HoleScore(
            hole_number=idx + 1,
            par=int(hole_scores_form[idx].par.data),
            fairway_hit=hole_scores_form[idx].fairway_hit.data,
            green_in_regulation=hole_scores_form[idx].green_in_regulation.data,
            putts=hole_scores_form[idx].putts.data,
            score=hole_scores_form[idx].score.data,
        )
        # Add each golf hole to GOLF ROUND
        golf_round.hole_scores.append(hole_score)

        # Track Par of Course
        golf_round.par += hole_score.par
        # Update the total score of the golf round
        golf_round.total_score += hole_score.score

        # Add to database
    db.session.commit()


#####################################################
# Golf Rounds Add/Show Previous Rounds/Edit/Delete
@app.route("/golf_round/add9", methods=["GET", "POST"])
def add_golf_round9():
    """Handle User Adding New Golf Round"""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = AddGolfRoundForm()

    if form.validate_on_submit():
        hole_count = int(form.hole_count.data)
        golf_round = create_golf_round(
            g.user.id, form.date_played.data, form.course_name.data
        )
        save_hole_scores(golf_round, form.hole_scores, hole_count)

        return redirect("/")

    return render_template("golf_round/add.html", form=form)


@app.route("/golf_round/add18", methods=["GET", "POST"])
def add_golf_round18():
    """Handle User Adding New Golf Round (18 HOLES)"""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = AddGolfRoundForm18()

    if form.validate_on_submit():
        hole_count = int(form.hole_count.data)
        golf_round = create_golf_round(
            g.user.id, form.date_played.data, form.course_name.data
        )
        save_hole_scores(golf_round, form.hole_scores, hole_count)

        return redirect("/")

    return render_template("golf_round/add.html", form=form)


@app.route("/golf_round/history")
def previous_rounds():
    """Show all previous rounds recorded"""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    golf_rounds = GolfRound.query.filter_by(user_id=g.user.id).all()

    # Calculates Over/Under Par
    for golf_round in golf_rounds:
        golf_round.difference = golf_round.total_score - golf_round.par

    return render_template("golf_round/history.html", golf_rounds=golf_rounds)


@app.route("/golf_round/<int:golf_round_id>")
def golf_round_details(golf_round_id):
    """Show detail on specific round"""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    golf_round = GolfRound.query.get_or_404(golf_round_id)

    return render_template("golf_round/details.html", golf_round=golf_round)


@app.route("/golf_round/<int:golf_round_id>/edit", methods=["GET", "POST"])
def golf_round_edit(golf_round_id):
    """Edit scores"""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    golf_round = GolfRound.query.get_or_404(golf_round_id)

    # Prepopulate Form
    form = AddGolfRoundForm(obj=golf_round)

    if form.validate_on_submit():
        # EDIT Golf Round Information
        golf_round.date_played = form.date_played.data
        golf_round.course_name = form.course_name.data
        golf_round.hole_count = int(form.hole_count.data)

        # EDIT Individual Holes
        for idx in range(golf_round.hole_count):
            hole = golf_round.hole_scores[idx]
            hole.hole_number = idx + 1
            hole.par = int(form.hole_scores[idx].par.data)
            hole.fairway_hit = form.hole_scores[idx].fairway_hit.data
            hole.green_in_regulation = form.hole_scores[idx].green_in_regulation.data
            hole.putts = form.hole_scores[idx].putts.data
            hole.score = form.hole_scores[idx].score.data
        # Add to DB
        db.session.commit()

        return redirect(f"/golf_round/{golf_round_id}")

    return render_template("golf_round/edit.html", form=form)


@app.route("/golf_round/<int:golf_round_id>/delete", methods=["POST"])
def delete_golf_round(golf_round_id):
    """Delete Golf Round"""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    # Get golf round
    golf_round = GolfRound.query.get_or_404(golf_round_id)

    # Delete associated holes with golf round first
    HoleScore.query.filter_by(golf_round_id=golf_round_id).delete()

    # Delete golf round
    db.session.delete(golf_round)
    db.session.commit()

    return redirect("/golf_round/history")


####################################################################################################################


# GOLF BLOG API's
@app.route("/golf_news")
def show_golf_news():
    """Display Golf News Home Page"""
    return render_template("/golf_news/home.html", time=time.time())


@app.route("/golf_news/schedule")
def show_PGA_schedule():
    """Display PGA schedule base on season"""

    # Fetch PGA schedule data from API
    # response = requests.get(f"{BASE_URL}/Tournaments/2023?{URL_KEY}")
    response = requests.get("https://api.sportsdata.io/golf/v2/json/Tournaments/2023?key=176964ab9ddb48dea44c9fb38e4adbc8")
    tournaments = response.json()
    return render_template("golf_news/schedule.html", time=time.time(), tournaments=tournaments)


@app.route("/golf_news/leaderboard/<int:tournament_id>")
def show_tournament_leaderboard(tournament_id):
    """Display Leaderboard of tournament"""

    # Fetch leaderboard data for the specified tournament from API
    response = requests.get(f"https://api.sportsdata.io/golf/v2/json/Leaderboard/{tournament_id}?key=176964ab9ddb48dea44c9fb38e4adbc8")
    leaderboard_data = response.json()
    return render_template("golf_news/leaderboard.html", leaderboard_data=leaderboard_data)
