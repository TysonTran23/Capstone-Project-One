from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    FieldList,
    FormField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Email, InputRequired, Length, NumberRange


class AddUserForm(FlaskForm):
    """Form for adding users"""

    username = StringField("Username", validators=[DataRequired()])
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[Length(min=6)])
    submit = SubmitField("Sign Up")


class LoginForm(FlaskForm):
    """Form for Loggin in User"""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[Length(min=6)])
    submit = SubmitField("Login")


class HoleScoreForm(FlaskForm):
    """Form for each hole"""

    par = SelectField("Par", choices=[("3", "Par 3"), ("4", "Par 4"), ("5", "Par 5")])
    fairway_hit = BooleanField("Fairway")
    green_in_regulation = BooleanField("Green in Regulation")
    putts = IntegerField("Putts", validators=[DataRequired(), NumberRange(min=0)])
    score = IntegerField("Score", validators=[DataRequired(), NumberRange(min=1)])


class AddGolfRoundForm(FlaskForm):
    """Form for adding Golf Round"""

    date_played = DateField("Date Played", validators=[InputRequired()])
    course_name = StringField("Course Name", validators=[InputRequired()])
    hole_count = SelectField(
        "Number of Holes",
        choices=[("9", "9 Holes")],
        validators=[InputRequired()],
    )
    hole_scores = FieldList(FormField(HoleScoreForm), min_entries=9, max_entries=18)
    submit = SubmitField("Submit Round")



class AddGolfRoundForm18(FlaskForm):
    """Form for adding Golf Round"""

    date_played = DateField("Date Played", validators=[InputRequired()])
    course_name = StringField("Course Name", validators=[InputRequired()])
    hole_count = SelectField(
        "Number of Holes",
        choices=[("18", "18 Holes")],
        validators=[InputRequired()],
    )
    hole_scores = FieldList(FormField(HoleScoreForm), min_entries=18, max_entries=18)
    submit = SubmitField("Submit Round")

