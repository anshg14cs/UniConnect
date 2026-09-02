import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g
from .universities import UK_UNIVERSITIES
from werkzeug.security import generate_password_hash, check_password_hash
from .db import get_db

def create_app():
    app = Flask(__name__)
    app.config["DATABASE"] = os.path.join(
    app.instance_path,
    "uniconnect.sqlite"
)

    os.makedirs(app.instance_path, exist_ok=True)

    from . import db
    db.init_app(app)

    app.config["SECRET_KEY"] = "dev"

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")

        if user_id is None:
            g.user = None

        else:
            g.user = get_db().execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/register" , methods=["GET", "POST"])
    def register():
        error = None
        name = ""
        email = ""
        university = ""

        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form["email"].strip()
            university = request.form["university"].strip()
            password = request.form["password"]
            confirm_password = request.form["confirm_password"]

            if not name or not email or not password or not confirm_password or not university:
                error = "All fields are required!"

            elif password != confirm_password:
                error = "Passwords do not match!"

            elif len(password) < 8:
                error = "Password must be at least 8 characters long."

            else:
                password_hash = generate_password_hash(password)
                db = get_db()

                try:

                    db.execute(
                        """
                        INSERT INTO users (name, university, email, password_hash)
                        VALUES (?, ?, ?, ?)
                        """,
                        (name, university, email, password_hash)
                    )

                    db.commit()
                    return redirect(url_for("home"))

                except sqlite3.IntegrityError:
                    error = "An account with that email already exists." 
    
        return render_template("register.html", error = error, name=name, email = email, university = university, universities = UK_UNIVERSITIES)
    
    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        email = ""

        if request.method == "POST":
            email = request.form["email"].strip()
            password = request.form["password"]

            db = get_db()

            user = db.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

            if user is None:
                error = "Incorrect email or password."

            elif not check_password_hash(user["password_hash"], password):
                error = "Incorrect email or password."

            else:
                session["user_id"] = user["id"]
                return redirect(url_for("home"))

        return render_template("login.html", error=error, email = email)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("home"))

    @app.route("/profile")
    def profile():
        if g.user is None:
            return redirect(url_for("login"))
        db = get_db()

        interests = db.execute(
            """
            SELECT interests.name
            FROM interests
            JOIN user_interests
                ON interests.id = user_interests.interest_id
            WHERE user_interests.user_id = ?
            """,
            (g.user["id"],)
        ).fetchall()

        return render_template(
            "profile.html",
            user=g.user,
            interests=interests
        )

    @app.route("/profile/edit", methods=["GET", "POST"])
    def edit_profile():
        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        if request.method == "POST":
            name = request.form["name"].strip()
            university = request.form["university"].strip()
            course = request.form["course"].strip()
            year_of_study = request.form["year_of_study"].strip()
            location = request.form["location"].strip()
            bio = request.form["bio"].strip()
            selected_interests = request.form.getlist("interests")


            db.execute(
                """
                UPDATE users
                SET name = ?,
                    university = ?,
                    course = ?,
                    year_of_study = ?,
                    location = ?,
                    bio = ?
                WHERE id = ?
                """,
                (
                    name,
                    university,
                    course,
                    year_of_study,
                    location,
                    bio,
                    g.user["id"]
                )
            )

            db.execute(
                "DELETE FROM user_interests WHERE user_id = ?",
                (g.user["id"],)
            )

            for interest_id in selected_interests:
                db.execute(
                    """
                    INSERT INTO user_interests (user_id, interest_id)
                    VALUES (?, ?)
                    """,
                    (g.user["id"], interest_id)
                )

            db.commit()

            return redirect(url_for("profile"))
        all_interests = db.execute(
                            """
                            SELECT *
                            FROM interests
                            ORDER BY name
                            """
                        ).fetchall()
        selected_interests = db.execute(
                            """
                            SELECT interest_id
                            FROM user_interests
                            WHERE user_id = ?
                            """,
                            (g.user["id"],)
                        ).fetchall()
        selected_interest_ids = [
            interest["interest_id"]
            for interest in selected_interests]


        return render_template("edit_profile.html", user=g.user, all_interests=all_interests, selected_interest_ids=selected_interest_ids)

    return app