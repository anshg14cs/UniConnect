import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from .universities import UK_UNIVERSITIES
from werkzeug.security import generate_password_hash
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

    return app