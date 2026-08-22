import os
from flask import Flask, render_template, request
from .universities import UK_UNIVERSITIES

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

        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form["email"].strip()
            password = request.form["password"]
            confirm_password = request.form["confirm_password"]

            if not name or not email or not password or not confirm_password:
                error = "All fields are required!"

            elif password != confirm_password:
                error = "Passwords do not match!"

            elif len(password) < 8:
                error = "Password must be at least 8 characters long."

            else:
                print("Registration data is valid")
        return render_template("register.html", error = error, name=name, email = email, universities = UK_UNIVERSITIES)

    return app