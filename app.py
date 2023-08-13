import datetime
import os
import pdb
import time

import requests
from flask import Flask, abort, flash, g, redirect, render_template, request, session
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError

from forms import (
    AddGolfRoundForm,
    AddGolfRoundForm18,
    AddUserForm,
    HoleScoreForm,
    LoginForm,
)
from models import GolfRound, HoleScore, User, connect_db, db

CURR_USER_KEY = "curr_user"

# API URL's
BASE_URL = "https:api.sportsdata.io/golf/v2/json"
URL_KEY = "key=176964ab9ddb48dea44c9fb38e4adbc8"

# Calculate current Year for API
CURRENT_YEAR = datetime.datetime.now().year


app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgresql:///golf_tracker"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
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
        # TRY to signup user
        try:
            user = User.signup(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
            )
            db.session.commit()

        # If username is already taken, show form, flash error message
        except IntegrityError:
            flash("Username already taken", "danger")
            return render_template("user/signup.html", form=form)

        # If user signup successful, redirect to homepage
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

    # Logout function
    do_logout()
    flash("You have successfully logged out", "success")

    return redirect("/login")


####################################################################################################################


def last_10_rounds():
    """Retrieve last 10 rounds of User"""

    # Golf Round filtered by user_id
    rounds = GolfRound.query.filter_by(user_id=g.user.id)

    # return a list of the rounds
    return [round.total_score for round in rounds][-10:]


def calculate_fairway_percentage(user_id):
    """Calculate fairway percentage base off of database"""

    # Grab HoleScore.fairway_hit column
    # If True, add 1, if False add 0
    # Sum items, which returns the amount of fairway hits
    fairway_hit_count = (
        db.session.query(func.sum(case([(HoleScore.fairway_hit == True, 1)], else_=0)))
        .join(GolfRound)
        .filter(GolfRound.user_id == user_id)
        .scalar()
    )
    # Find how much holes played by user
    total_holes_played = (
        db.session.query(func.count(HoleScore.id))
        .join(GolfRound)
        .filter(GolfRound.user_id == user_id)
        .scalar()
    )

    # Calculate the percentage of fairway hit
    # How many fairways player has hit / total holes
    fairway_percentage = (
        (fairway_hit_count / total_holes_played) * 100 if total_holes_played > 0 else 0
    )

    # Return fairway percentage to 2 decimal points
    return round(fairway_percentage, 2)


def calculate_greens_in_regulation(user_id):
    # Grab HoleScore.greens_in_regulation column
    # If True, add 1, if False add 0
    # Sum items, which returns the amount of fairway hits
    green_in_regulation = (
        db.session.query(
            func.sum(case([(HoleScore.green_in_regulation == True, 1)], else_=0))
        )
        .join(GolfRound)
        .filter(GolfRound.user_id == user_id)
        .scalar()
    )

    # Find how much holes played by user
    total_holes_played = (
        db.session.query(func.count(HoleScore.id))
        .join(GolfRound)
        .filter(GolfRound.user_id == user_id)
        .scalar()
    )

    # Calculate the greens in regulation percentage
    # Number of greens hit / Total holes played by user
    green_in_regulation_percentage = (
        (green_in_regulation / total_holes_played) * 100
        if total_holes_played > 0
        else 0
    )

    return round(green_in_regulation_percentage, 2)


def calculate_putts_per_round(user_id):
    # Grab HoleScore.putts column
    # Join and filter by user_id
    # Group and order from last 10 rounds
    last_10_rounds_putts = (
        db.session.query(func.sum(HoleScore.putts))
        .join(GolfRound)
        .filter(GolfRound.user_id == user_id)
        .group_by(GolfRound.id)
        .order_by(GolfRound.date_played.desc())
        .limit(10)
        .all()
    )

    # The query will return a list of tuples. Each tuple has one element (the total number of putts for a round). This line of code converts that list of one-element tuples into a plain list of integers. For example, it'll convert [(5,), (6,), (7,)] to [5, 6, 7].
    last_10_rounds_putts = [total_putts for (total_putts,) in last_10_rounds_putts]

    return last_10_rounds_putts


def calculate_average_scores(user_id):
    """Calculate the AVG SCORE"""

    # Avg score of all Total_Scores
    avg_score_18 = (
        db.session.query(func.avg(GolfRound.total_score))
        .filter(GolfRound.user_id == user_id)
        .scalar()
    )
    # Avg score of all Total_Scores / 2
    avg_score_9 = (
        db.session.query(func.avg(GolfRound.total_score / 2))
        .filter(GolfRound.user_id == user_id)
        .scalar()
    )

    # Avg Score on Holes that are Par 3's
    avg_par_3 = (
        db.session.query(func.avg(HoleScore.score))
        .join(GolfRound)
        .filter(GolfRound.user_id == user_id, HoleScore.par == 3)
        .scalar()
    )
    # Avg Score on Holes that are Par 4's
    avg_par_4 = (
        db.session.query(func.avg(HoleScore.score))
        .join(GolfRound)
        .filter(GolfRound.user_id == user_id, HoleScore.par == 4)
        .scalar()
    )
    # Avg Score on Holes that are Par 5's
    avg_par_5 = (
        db.session.query(func.avg(HoleScore.score))
        .join(GolfRound)
        .filter(GolfRound.user_id == user_id, HoleScore.par == 5)
        .scalar()
    )

    # Return Scores, if None than default to 0.0
    return (
        round(avg_score_18, 2) if avg_score_18 is not None else 0.0,
        round(avg_score_9, 2) if avg_score_9 is not None else 0.0,
        round(avg_par_3, 2) if avg_par_3 is not None else 0.0,
        round(avg_par_4, 2) if avg_par_4 is not None else 0.0,
        round(avg_par_5, 2) if avg_par_5 is not None else 0.0,
    )


def scores(user_id):
    """Keeps tracks of eagles, birdies, pars, bogies, doubles and triples"""

    golf_rounds = GolfRound.query.filter_by(user_id=g.user.id).all()

    # Grabs the columns Score and Par
    hole_scores_and_pars = (
        db.session.query(HoleScore.score, HoleScore.par)
        .join(GolfRound)
        .filter(GolfRound.user_id == user_id)
        .all()
    )
    # Create a dictionary of stats
    categories = {
        "eagles": 0,
        "birdies": 0,
        "pars": 0,
        "bogies": 0,
        "double_bogies": 0,
        "triples": 0,
        "double_pars": 0,
    }
    # Calculate the difference
    # According to result, add 1 to eagles, birdies, pars, etc
    for score, par in hole_scores_and_pars:
        score_difference = score - par

        if score_difference <= -2:
            categories["eagles"] += 1
        elif score_difference == -1:
            categories["birdies"] += 1
        elif score_difference == 0:
            categories["pars"] += 1
        elif score_difference == 1:
            categories["bogies"] += 1
        elif score_difference == 2:
            categories["double_bogies"] += 1
        elif score_difference == 3:
            categories["triples"] += 1
        elif score_difference >= 4:
            categories["double_pars"] += 1

    # Return dictionary of stats
    return categories


def get_progress_color(percentage):
    """This function is used to produce red to green depending on percentags
    Lower the percentage = Red
    Higher the percentage = Green
    """

    red = min(255, 255 - (percentage * 2.55))
    green = min(255, percentage * 2.55)
    return f"rgb({int(red)}, {int(green)}, 0)"


@app.route("/")
def home_page():
    #Makes sure user are signed in before accessing page
    if g.user:

        #Last 5 Rounds and Score to par 
        golf_rounds = (
            GolfRound.query.filter_by(user_id=g.user.id)
            .order_by(GolfRound.date_played.desc())
            .limit(5)
            .all()
        )
        for golf_round in golf_rounds:
            golf_round.difference = golf_round.total_score - golf_round.par

        #Get's progress bar color for fairway and greens hit percentages
        fairway_hit_percentage_color = get_progress_color(
            calculate_fairway_percentage(g.user.id)
        )
        green_in_regulation_color = get_progress_color(
            calculate_greens_in_regulation(g.user.id)
        )

        #Return template and stats from previous functions 
        return render_template(
            "home.html",
            last_10_score=last_10_rounds(),
            fairway_hit_percentage=calculate_fairway_percentage(g.user.id),
            green_in_regulation=calculate_greens_in_regulation(g.user.id),
            last_10_round_putts=calculate_putts_per_round(g.user.id),
            avg_scores=calculate_average_scores(g.user.id),
            scores=scores(g.user.id),
            golf_rounds=golf_rounds,
            fairway_hit_percentage_color=fairway_hit_percentage_color,
            green_in_regulation_color=green_in_regulation_color,
            time=time.time(),
        )
    #If NOT g.user, return them to the home page
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
    
    #if not logged in 
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

    return render_template("golf_round/add9.html", form=form)


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

    return render_template("golf_round/add18.html", form=form)


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
    response = requests.get(
        f"https://api.sportsdata.io/golf/v2/json/Tournaments/{CURRENT_YEAR}?key=176964ab9ddb48dea44c9fb38e4adbc8"
    )
    tournaments = response.json()
    return render_template(
        "golf_news/schedule.html", time=time.time(), tournaments=tournaments
    )


@app.route("/golf_news/leaderboard/<int:tournament_id>")
def show_tournament_leaderboard(tournament_id):
    """Display Leaderboard of tournament"""

    # Fetch leaderboard data for the specified tournament from API
    response = requests.get(
        f"https://api.sportsdata.io/golf/v2/json/Leaderboard/{tournament_id}?key=176964ab9ddb48dea44c9fb38e4adbc8"
    )
    leaderboard_data = response.json()
    return render_template(
        "golf_news/leaderboard.html", leaderboard_data=leaderboard_data
    )


@app.route("/golf_news/current_leaderboard")
def show_current_leaderboard():
    """Display Current Tournament Leaderboard"""
    return render_template("golf_news/current_leaderboard.html", time=time.time())


@app.route("/golf_news/world_rankings")
def show_world_rankings():
    """Display World Rankings"""
    response = requests.get(
        f"https://api.sportsdata.io/golf/v2/json/PlayerSeasonStats/{CURRENT_YEAR}?key=176964ab9ddb48dea44c9fb38e4adbc8"
    )
    rankings = response.json()
    return render_template(
        "golf_news/world_rankings.html", rankings=rankings, time=time.time()
    )


@app.route("/golf_news/player/<int:player_id>")
def show_player_details(player_id):
    """Display Player Details"""
    response = requests.get(
        f"https://api.sportsdata.io/golf/v2/json/Player/{player_id}?key=176964ab9ddb48dea44c9fb38e4adbc8"
    )
    response2 = requests.get(
        f"https://api.sportsdata.io/golf/v2/json/NewsByPlayerID/{player_id}?key=176964ab9ddb48dea44c9fb38e4adbc8"
    )
    player = response.json()
    news = response2.json()
    return render_template("golf_news/player.html", player=player, news=news)


####################################################################################################################
