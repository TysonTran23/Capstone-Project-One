import os
import pdb
import time

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
# Golf Rounds Add/Show Previous Rounds/Edit/Delete
@app.route("/golf_round/add", methods=["GET", "POST"])
def add_golf_round():
    """Handle User Adding New Golf Round"""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

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
            par=0,
            total_score=0,
        )

        # Retrieving data for individual holes from forms
        # Create Each Golf Hole Instance
        for idx in range(hole_count):
            hole_score = HoleScore(
                hole_number=idx + 1,
                par=int(form.hole_scores[idx].par.data),
                fairway_hit=form.hole_scores[idx].fairway_hit.data,
                green_in_regulation=form.hole_scores[idx].green_in_regulation.data,
                putts=form.hole_scores[idx].putts.data,
                score=form.hole_scores[idx].score.data,
            )
            # Add each golf hole to GOLF ROUND
            golf_round.hole_scores.append(hole_score)

            # Track Par of Course
            golf_round.par += hole_score.par
            # Update the total score of the golf round
            golf_round.total_score += hole_score.score

            # Add to database
            db.session.add(golf_round)
            db.session.commit()

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
@app.route("/golf_blog")
def show_blog():
    return render_template("/golf_blog/blog.html", time=time.time())
