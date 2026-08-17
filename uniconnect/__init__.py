from flask import Flask, render_template, request


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/register" , methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            print(request.form)
        return render_template("register.html")

    return app