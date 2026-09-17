import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, abort, jsonify
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

            friend_request_result = db.execute(
                """
                SELECT COUNT(*) AS count
                FROM friend_requests
                WHERE receiver_id = ?
                AND status = 'pending'
                """,
                (user_id,)
            ).fetchone()

            social_notification_result = db.execute(
                """
                SELECT COUNT(*) AS count
                FROM notifications
                WHERE recipient_id = ?
                AND is_read = 0
                """,
                (user_id,)
            ).fetchone()

            g.notification_count = (friend_request_result["count"] + social_notification_result["count"])

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


        social_notifications = db.execute(
            """
            SELECT
                notifications.id,
                notifications.type,
                notifications.post_id,
                notifications.comment_id,
                notifications.conversation_id,
                notifications.message_id,
                notifications.is_read,
                notifications.created_at,

                users.id AS actor_id,
                users.name AS actor_name,
                users.university AS actor_university,

                comments.content AS comment_content,
                messages.content AS message_content

            FROM notifications

            JOIN users
                ON notifications.actor_id = users.id

            LEFT JOIN comments
                ON notifications.comment_id = comments.id

            LEFT JOIN messages
                ON notifications.message_id = messages.id

            WHERE notifications.recipient_id = ?

            ORDER BY notifications.created_at DESC
            """,
            (g.user["id"],)
        ).fetchall()

        db.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE recipient_id = ?
            AND is_read = 0
            """,
            (g.user["id"],)
        )

        db.commit()

        g.notification_count = len(friend_requests)


        return render_template(
            "notifications.html",
            friend_requests=friend_requests,
            social_notifications=social_notifications
        )

    @app.route("/notifications/count")
    def notification_count():

        if g.user is None:
            return jsonify({"count": 0})

        db = get_db()

        friend_request_result = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM friend_requests
            WHERE receiver_id = ?
            AND status = 'pending'
            """,
            (g.user["id"],)
        ).fetchone()

        social_notification_result = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM notifications
            WHERE recipient_id = ?
            AND is_read = 0
            """,
            (g.user["id"],)
        ).fetchone()

        count = (
            friend_request_result["count"]
            +
            social_notification_result["count"]
        )

        return jsonify({
            "count": count
        })

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

        return redirect(url_for("feed"))
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
    @app.route("/feed")
    def feed():

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        posts = db.execute(
            """
            SELECT
                posts.id,
                posts.content,
                posts.created_at,

                users.id AS user_id,
                users.name,
                users.university,

                (
                    SELECT COUNT(*)
                    FROM comments
                    WHERE comments.post_id = posts.id
                ) AS comment_count,

                (
                    SELECT COUNT(*)
                    FROM post_likes
                    WHERE post_likes.post_id = posts.id
                ) AS like_count,

                EXISTS (
                    SELECT 1
                    FROM post_likes
                    WHERE post_likes.post_id = posts.id
                    AND post_likes.user_id = ?
                ) AS liked_by_user

            FROM posts

            JOIN users
                ON posts.user_id = users.id

            WHERE posts.user_id = ?

            OR EXISTS (
                SELECT 1
                FROM friend_requests

                WHERE friend_requests.status = 'accepted'

                AND (
                    (
                        friend_requests.sender_id = ?
                        AND friend_requests.receiver_id = posts.user_id
                    )

                    OR

                    (
                        friend_requests.receiver_id = ?
                        AND friend_requests.sender_id = posts.user_id
                    )
                )
            )

            ORDER BY posts.created_at DESC
            """,
            (
                g.user["id"],
                g.user["id"],
                g.user["id"],
                g.user["id"]
            )
        ).fetchall()

        comments_by_post = {}

        if posts:

            post_ids = [post["id"] for post in posts]

            placeholders = ",".join(
                "?" for post_id in post_ids
            )

            comments = db.execute(
                f"""
                SELECT
                    comments.id,
                    comments.post_id,
                    comments.content,
                    comments.created_at,

                    users.id AS user_id,
                    users.name

                FROM comments

                JOIN users
                    ON comments.user_id = users.id

                WHERE comments.post_id IN ({placeholders})

                ORDER BY comments.created_at ASC
                """,
                post_ids
            ).fetchall()


            for comment in comments:

                post_id = comment["post_id"]

                if post_id not in comments_by_post:
                    comments_by_post[post_id] = []

                comments_by_post[post_id].append(comment)
         

        return render_template(
            "feed.html",
            posts=posts,
            comments_by_post=comments_by_post
        )

    @app.route("/posts/<int:post_id>/like", methods=["POST"])
    def toggle_like(post_id):

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        post = db.execute(
            """
            SELECT *
            FROM posts
            WHERE id = ?
            """,
            (post_id,)
        ).fetchone()

        if post is None:
            abort(404)

        existing_like = db.execute(
            """
            SELECT *
            FROM post_likes
            WHERE user_id = ?
            AND post_id = ?
            """,
            (g.user["id"], post_id)
        ).fetchone()


        if existing_like is None:

            db.execute(
                """
                INSERT INTO post_likes (user_id, post_id)
                VALUES (?, ?)
                """,
                (g.user["id"], post_id)
            )

            # Create a notification only when liking
            # somebody else's post
            if post["user_id"] != g.user["id"]:

                db.execute(
                    """
                    INSERT INTO notifications (
                        recipient_id,
                        actor_id,
                        type,
                        post_id
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        post["user_id"],
                        g.user["id"],
                        "like",
                        post_id
                    )
                )


        else:

            db.execute(
                """
                DELETE FROM post_likes
                WHERE user_id = ?
                AND post_id = ?
                """,
                (g.user["id"], post_id)
            )

            db.execute(
                """
                DELETE FROM notifications
                WHERE recipient_id = ?
                AND actor_id = ?
                AND type = 'like'
                AND post_id = ?
                """,
                (
                    post["user_id"],
                    g.user["id"],
                    post_id
                )
            )


        db.commit()

        return redirect(url_for("feed"))
         

    @app.route("/posts/<int:post_id>/comments/create", methods=["POST"])
    def create_comment(post_id):

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        post = db.execute(
            """
            SELECT *
            FROM posts
            WHERE id = ?
            """,
            (post_id,)
        ).fetchone()

        if post is None:
            abort(404)

        content = request.form["content"].strip()

        if content:

            cursor = db.execute(
                """
                INSERT INTO comments (post_id, user_id, content)
                VALUES (?, ?, ?)
                """,
                (
                    post_id,
                    g.user["id"],
                    content
                )
            )

            comment_id = cursor.lastrowid

            if post["user_id"] != g.user["id"]:

                db.execute(
                    """
                    INSERT INTO notifications (
                        recipient_id,
                        actor_id,
                        type,
                        post_id,
                        comment_id
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        post["user_id"],
                        g.user["id"],
                        "comment",
                        post_id,
                        comment_id
                    )
                )

            db.commit()

        return redirect(url_for("feed"))
    
    @app.route("/posts/<int:post_id>/delete", methods=["POST"])
    def delete_post(post_id):

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        post = db.execute(
            """
            SELECT *
            FROM posts
            WHERE id = ?
            """,
            (post_id,)
        ).fetchone()

        if post is None:
            abort(404)

        if post["user_id"] != g.user["id"]:
            abort(403)

        db.execute(
            """
            DELETE FROM notifications
            WHERE post_id = ?
            """,
            (post_id,)
        )

        db.execute(
            """
            DELETE FROM post_likes
            WHERE post_id = ?
            """,
            (post_id,)
        )

        db.execute(
            """
            DELETE FROM comments
            WHERE post_id = ?
            """,
            (post_id,)
        )

        db.execute(
            """
            DELETE FROM posts
            WHERE id = ?
            """,
            (post_id,)
        )

        db.commit()

        return redirect(url_for("feed"))

    @app.route("/comments/<int:comment_id>/delete", methods=["POST"])
    def delete_comment(comment_id):

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        comment = db.execute(
            """
            SELECT *
            FROM comments
            WHERE id = ?
            """,
            (comment_id,)
        ).fetchone()

        if comment is None:
            abort(404)

        if comment["user_id"] != g.user["id"]:
            abort(403)

        db.execute(
            """
            DELETE FROM notifications
            WHERE comment_id = ?
            """,
            (comment_id,)
        )

        db.execute(
            """
            DELETE FROM comments
            WHERE id = ?
            """,
            (comment_id,)
        )

        db.commit()

        return redirect(url_for("feed"))

    @app.route("/messages/start/<int:user_id>", methods=["POST"])
    def start_conversation(user_id):

        if g.user is None:
            return redirect(url_for("login"))

        if user_id == g.user["id"]:
            abort(400)

        db = get_db()


        # Check that the other user exists
        other_user = db.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        if other_user is None:
            abort(404)


        # Users must be accepted connections
        friendship = db.execute(
            """
            SELECT *
            FROM friend_requests
            WHERE status = 'accepted'
            AND (
                (sender_id = ? AND receiver_id = ?)
                OR
                (sender_id = ? AND receiver_id = ?)
            )
            """,
            (
                g.user["id"],
                user_id,
                user_id,
                g.user["id"]
            )
        ).fetchone()

        if friendship is None:
            abort(403)


        # Look for an existing 1-to-1 conversation
        conversation = db.execute(
            """
            SELECT conversations.id

            FROM conversations

            JOIN conversation_members AS member_one
                ON conversations.id = member_one.conversation_id

            JOIN conversation_members AS member_two
                ON conversations.id = member_two.conversation_id

            WHERE member_one.user_id = ?
            AND member_two.user_id = ?

            AND (
                SELECT COUNT(*)
                FROM conversation_members
                WHERE conversation_id = conversations.id
            ) = 2

            LIMIT 1
            """,
            (
                g.user["id"],
                user_id
            )
        ).fetchone()


        if conversation is None:

            cursor = db.execute(
                """
                INSERT INTO conversations DEFAULT VALUES
                """
            )

            conversation_id = cursor.lastrowid

            db.execute(
                """
                INSERT INTO conversation_members (
                    conversation_id,
                    user_id
                )
                VALUES (?, ?)
                """,
                (
                    conversation_id,
                    g.user["id"]
                )
            )

            db.execute(
                """
                INSERT INTO conversation_members (
                    conversation_id,
                    user_id
                )
                VALUES (?, ?)
                """,
                (
                    conversation_id,
                    user_id
                )
            )

            db.commit()

        else:

            conversation_id = conversation["id"]


        return redirect(
            url_for(
                "conversation",
                conversation_id=conversation_id
            )
        )

    @app.route("/messages/<int:conversation_id>")
    def conversation(conversation_id):

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()


        # Make sure the logged-in user belongs to this conversation
        membership = db.execute(
            """
            SELECT *
            FROM conversation_members
            WHERE conversation_id = ?
            AND user_id = ?
            """,
            (
                conversation_id,
                g.user["id"]
            )
        ).fetchone()

        if membership is None:
            abort(403)


        # Get the other person in the conversation
        other_user = db.execute(
            """
            SELECT users.*

            FROM conversation_members

            JOIN users
                ON conversation_members.user_id = users.id

            WHERE conversation_members.conversation_id = ?
            AND conversation_members.user_id != ?
            """,
            (
                conversation_id,
                g.user["id"]
            )
        ).fetchone()

        if other_user is None:
            abort(404)


        # Load all messages in chronological order
        messages = db.execute(
            """
            SELECT
                messages.id,
                messages.content,
                messages.created_at,
                messages.sender_id,
                users.name AS sender_name

            FROM messages

            JOIN users
                ON messages.sender_id = users.id

            WHERE messages.conversation_id = ?

            ORDER BY messages.created_at ASC
            """,
            (conversation_id,)
        ).fetchall()

        if messages:

            latest_message_id = messages[-1]["id"]

            db.execute(
                """
                UPDATE conversation_members
                SET last_read_message_id = ?
                WHERE conversation_id = ?
                AND user_id = ?
                """,
                (
                    latest_message_id,
                    conversation_id,
                    g.user["id"]
                )
            )

        db.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE recipient_id = ?
            AND conversation_id = ?
            AND type = 'message'
            AND is_read = 0
            """,
            (
                g.user["id"],
                conversation_id
            )
        )

        db.commit()

        friend_request_result = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM friend_requests
            WHERE receiver_id = ?
            AND status = 'pending'
            """,
            (g.user["id"],)
        ).fetchone()


        social_notification_result = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM notifications
            WHERE recipient_id = ?
            AND is_read = 0
            """,
            (g.user["id"],)
        ).fetchone()


        g.notification_count = (
            friend_request_result["count"]
            +
            social_notification_result["count"]
        )


        return render_template(
            "conversation.html",
            conversation_id=conversation_id,
            other_user=other_user,
            messages=messages
        )

    @app.route("/messages/<int:conversation_id>/send", methods=["POST"])
    def send_message(conversation_id):

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()


        # Make sure the logged-in user belongs to this conversation
        membership = db.execute(
            """
            SELECT *
            FROM conversation_members
            WHERE conversation_id = ?
            AND user_id = ?
            """,
            (
                conversation_id,
                g.user["id"]
            )
        ).fetchone()

        if membership is None:
            abort(403)


        # Find the other person in the conversation
        recipient = db.execute(
            """
            SELECT user_id
            FROM conversation_members
            WHERE conversation_id = ?
            AND user_id != ?
            """,
            (
                conversation_id,
                g.user["id"]
            )
        ).fetchone()

        if recipient is None:
            abort(404)


        content = request.form["content"].strip()

        if content:

            cursor = db.execute(
                """
                INSERT INTO messages (
                    conversation_id,
                    sender_id,
                    content
                )
                VALUES (?, ?, ?)
                """,
                (
                    conversation_id,
                    g.user["id"],
                    content
                )
            )

            message_id = cursor.lastrowid


            db.execute(
                """
                INSERT INTO notifications (
                    recipient_id,
                    actor_id,
                    type,
                    conversation_id,
                    message_id
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    recipient["user_id"],
                    g.user["id"],
                    "message",
                    conversation_id,
                    message_id
                )
            )

            db.commit()


        return redirect(
            url_for(
                "conversation",
                conversation_id=conversation_id,
            )
        )

    @app.route("/messages")
    def messages_inbox():

        if g.user is None:
            return redirect(url_for("login"))

        db = get_db()

        conversations = db.execute(
            """
            SELECT
                conversations.id AS conversation_id,

                users.id AS user_id,
                users.name,
                users.university,

                (
                    SELECT messages.content
                    FROM messages
                    WHERE messages.conversation_id = conversations.id
                    ORDER BY messages.created_at DESC, messages.id DESC
                    LIMIT 1
                ) AS last_message,

                (
                    SELECT messages.created_at
                    FROM messages
                    WHERE messages.conversation_id = conversations.id
                    ORDER BY messages.created_at DESC, messages.id DESC
                    LIMIT 1
                ) AS last_message_time,

                (
                    SELECT COUNT(*)
                    FROM messages
                    WHERE messages.conversation_id = conversations.id
                    AND messages.sender_id != ?
                    AND messages.id > COALESCE(
                        current_member.last_read_message_id,
                        0
                    )
                ) AS unread_count

            FROM conversations

            JOIN conversation_members AS current_member
                ON conversations.id = current_member.conversation_id

            JOIN conversation_members AS other_member
                ON conversations.id = other_member.conversation_id
                AND other_member.user_id != current_member.user_id

            JOIN users
                ON other_member.user_id = users.id

            WHERE current_member.user_id = ?

            AND (
                SELECT COUNT(*)
                FROM conversation_members
                WHERE conversation_id = conversations.id
            ) = 2

            ORDER BY
                CASE
                    WHEN last_message_time IS NULL
                        THEN conversations.created_at
                    ELSE last_message_time
                END DESC
            """,
            (
                g.user["id"],
                g.user["id"]
            )
        ).fetchall()

        return render_template(
            "messages.html",
            conversations=conversations
        )

    @app.route("/messages/unread")
    def message_unread_counts():

        if g.user is None:
            return jsonify({
                "total": 0,
                "conversations": {}
            })

        db = get_db()

        results = db.execute(
            """
            SELECT
                conversation_members.conversation_id,

                (
                    SELECT COUNT(*)
                    FROM messages

                    WHERE messages.conversation_id =
                        conversation_members.conversation_id

                    AND messages.sender_id != ?

                    AND messages.id > COALESCE(
                        conversation_members.last_read_message_id,
                        0
                    )
                ) AS unread_count

            FROM conversation_members

            WHERE conversation_members.user_id = ?
            """,
            (
                g.user["id"],
                g.user["id"]
            )
        ).fetchall()

        conversations = {
            str(result["conversation_id"]): result["unread_count"]
            for result in results
        }

        total = sum(conversations.values())

        return jsonify({
            "total": total,
            "conversations": conversations
        })
    return app



