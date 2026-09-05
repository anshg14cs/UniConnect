import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, abort
from .universities import UK_UNIVERSITIES
from werkzeug.security import generate_password_hash, check_password_hash
from .db import get_db
from datetime import datetime, timezone

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
            g.notification_count = 0

        else:
            db = get_db()
            g.user = get_db().execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()

            result = db.execute(
                """
                SELECT COUNT(*) AS count
                FROM friend_requests
                WHERE receiver_id = ?
                AND status = 'pending'
                """,
                (user_id,)
            ).fetchone()

            g.notification_count = result["count"]

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

        connection_result = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM friend_requests
            WHERE status = 'accepted'
            AND (sender_id = ? OR receiver_id = ?)
            """,
            (
                g.user["id"],
                g.user["id"]
            )
        ).fetchone()

        connection_count = connection_result["count"]

        posts = db.execute(
            """
            SELECT
                posts.id,
                posts.content,
                posts.created_at

            FROM posts

            WHERE posts.user_id = ?

            ORDER BY posts.created_at DESC
            """,
            (g.user["id"],)
        ).fetchall()

        post_result = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM posts
            WHERE user_id = ?
            """,
            (g.user["id"],)
        ).fetchone()

        post_count = post_result["count"]

        return render_template(
            "profile.html",
            user=g.user,
            interests=interests,
            connection_count = connection_count,
            posts = posts,
            post_count = post_count
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

    @app.route("/users/<int:user_id>")
    def user_profile(user_id):
        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        user = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        if user is None:
            abort(404)

        interests = db.execute(
            """
            SELECT interests.name
            FROM interests
            JOIN user_interests
                ON interests.id = user_interests.interest_id
            WHERE user_interests.user_id = ?
            """,
            (user_id,)
        ).fetchall()

        connection_result = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM friend_requests
            WHERE status = 'accepted'
            AND (sender_id = ? OR receiver_id = ?)
            """,
            (
                user_id,
                user_id
            )
        ).fetchone()

        connection_count = connection_result["count"]

        relationship = db.execute(
            """
            SELECT *
            FROM friend_requests
            WHERE
                (sender_id = ? AND receiver_id = ?)
                OR
                (sender_id = ? AND receiver_id = ?)
            """,
            (
                g.user["id"],
                user_id,
                user_id,
                g.user["id"]
            )
        ).fetchone()

        posts = db.execute(
            """
            SELECT
                posts.id,
                posts.content,
                posts.created_at

            FROM posts

            WHERE posts.user_id = ?

            ORDER BY posts.created_at DESC
            """,
            (user_id,)
        ).fetchall()

        post_result = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM posts
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        post_count = post_result["count"]

        return render_template(
            "profile.html",
            user=user,
            interests=interests,
            relationship = relationship,
            connection_count = connection_count,
            posts = posts,
            post_count = post_count
        )

    @app.route("/friend-request/<int:request_id>/accept", methods=["POST"])
    def accept_friend_request(request_id):

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        friend_request = db.execute(
            """
            SELECT *
            FROM friend_requests
            WHERE id = ?
            """,
            (request_id,)
        ).fetchone()

        if friend_request is None:
            abort(404)

        if friend_request["receiver_id"] != g.user["id"]:
            abort(403)

        db.execute(
            """
            UPDATE friend_requests
            SET status = 'accepted'
            WHERE id = ?
            """,
            (request_id,)
        )

        db.commit()

        return redirect(
            url_for("user_profile", user_id=friend_request["sender_id"])
        )

    @app.route("/friend-request/<int:request_id>/reject", methods=["POST"])
    def reject_friend_request(request_id):

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        friend_request = db.execute(
            """
            SELECT *
            FROM friend_requests
            WHERE id = ?
            """,
            (request_id,)
        ).fetchone()

        if friend_request is None:
            abort(404)

        if friend_request["receiver_id"] != g.user["id"]:
            abort(403)

        db.execute(
            """
            DELETE FROM friend_requests
            WHERE id = ?
            """,
            (request_id,)
        )

        db.commit()

        return redirect(
            url_for("user_profile", user_id=friend_request["sender_id"])
        )
    
    @app.route("/students")
    def students():
        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        search = request.args.get("search", "").strip()

        users = db.execute(
            """
            SELECT *
            FROM users
            WHERE id != ?
            ORDER BY name
            """,
            (g.user["id"],)
        ).fetchall()

        if search:
            users = db.execute(
                """
                SELECT *
                FROM users
                WHERE id != ?
                AND (
                    name LIKE ?
                    OR university LIKE ?
                    OR course LIKE ?
                )
                ORDER BY name
                """,
                (
                    g.user["id"],
                    f"%{search}%",
                    f"%{search}%",
                    f"%{search}%"
                )
            ).fetchall()

        else:
            users = db.execute(
                """
                SELECT *
                FROM users
                WHERE id != ?
                ORDER BY name
                """,
                (g.user["id"],)
            ).fetchall()

        return render_template(
            "students.html",
            users=users,
            search = search
        )

    @app.route("/friend-request/<int:receiver_id>", methods=["POST"])
    def send_friend_request(receiver_id):

        if g.user is None:
            return redirect(url_for("login"))

        if receiver_id == g.user["id"]:
            return redirect(url_for("profile"))

        db = get_db()

        receiver = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (receiver_id,)
        ).fetchone()

        if receiver is None:
            abort(404)

        existing_request = db.execute(
            """
            SELECT *
            FROM friend_requests
            WHERE
                (sender_id = ? AND receiver_id = ?)
                OR
                (sender_id = ? AND receiver_id = ?)
            """,
            (
                g.user["id"],
                receiver_id,
                receiver_id,
                g.user["id"]
            )
        ).fetchone()

        if existing_request is None:
            db.execute(
                """
                INSERT INTO friend_requests (sender_id, receiver_id)
                VALUES (?, ?)
                """,
                (g.user["id"], receiver_id)
            )

            db.commit()

        return redirect(url_for("user_profile", user_id=receiver_id))

    @app.route("/notifications")
    def notifications():

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        friend_requests = db.execute(
            """
            SELECT
                friend_requests.id AS request_id,
                users.id AS user_id,
                users.name,
                users.university

            FROM friend_requests

            JOIN users
                ON friend_requests.sender_id = users.id

            WHERE friend_requests.receiver_id = ?
            AND friend_requests.status = 'pending'

            ORDER BY friend_requests.id DESC
            """,
            (g.user["id"],)
        ).fetchall()

        return render_template(
            "notifications.html",
            friend_requests=friend_requests
        )

    @app.route("/users/<int:user_id>/connections")
    def user_connections(user_id):

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        if user is None:
            abort(404)

        connections = db.execute(
            """
            SELECT
                users.id,
                users.name,
                users.university,
                users.course

            FROM friend_requests

            JOIN users
                ON friend_requests.receiver_id = users.id

            WHERE friend_requests.sender_id = ?
            AND friend_requests.status = 'accepted'


            UNION


            SELECT
                users.id,
                users.name,
                users.university,
                users.course

            FROM friend_requests

            JOIN users
                ON friend_requests.sender_id = users.id

            WHERE friend_requests.receiver_id = ?
            AND friend_requests.status = 'accepted'

            ORDER BY name
            """,
            (user_id, user_id)
        ).fetchall()

        return render_template(
            "connections.html",
            user=user,
            connections=connections
        )

    @app.route("/posts/create", methods=["POST"])
    def create_post():

        if g.user is None:
            return redirect(url_for("login"))

        content = request.form["content"].strip()

        if not content:
            return redirect(url_for("profile"))

        db = get_db()

        db.execute(
            """
            INSERT INTO posts (user_id, content)
            VALUES (?, ?)
            """,
            (g.user["id"], content)
        )

        db.commit()

        return redirect(url_for("profile"))
    @app.template_filter("time_ago")
    def time_ago(timestamp):

        posted_time = datetime.strptime(
            timestamp,
            "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)

        current_time = datetime.now(timezone.utc)

        difference = current_time - posted_time

        seconds = int(difference.total_seconds())

        if seconds < 60:
            return "Just now"

        minutes = seconds // 60

        if minutes < 60:
            if minutes == 1:
                return "1 minute ago"

            return f"{minutes} minutes ago"

        hours = minutes // 60

        if hours < 24:
            if hours == 1:
                return "1 hour ago"

            return f"{hours} hours ago"

        days = hours // 24

        if days == 1:
            return "Yesterday"

        if days < 7:
            return f"{days} days ago"

        weeks = days // 7

        if weeks == 1:
            return "1 week ago"

        return f"{weeks} weeks ago"

    return app



