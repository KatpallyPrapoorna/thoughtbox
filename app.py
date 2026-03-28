import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session
from flask_wtf.csrf import CSRFProtect
import bleach

from models import db, Insight

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = (
    os.getenv("DATABASE_URL") or "sqlite:///data.db"
).replace("postgres://", "postgresql://")

db.init_app(app)
csrf = CSRFProtect(app)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

with app.app_context():
    db.create_all()


def clean(text):
    return bleach.clean(text or "", strip=True)


# HOME
@app.route("/")
def index():
    search = request.args.get("search", "")
    category = request.args.get("category", "")

    query = Insight.query

    if search:
        query = query.filter(Insight.insight.contains(search))

    if category:
        query = query.filter(Insight.category == category)

    insights = Insight.query.order_by(Insight.created_at.desc()).all()

    return render_template("index.html", insights=insights, search=search, category=category)


# SUBMIT
@app.route("/submit", methods=["POST"])
def submit():
    name = clean(request.form.get("name"))
    book = clean(request.form.get("book_name"))
    category = clean(request.form.get("category"))
    insight = clean(request.form.get("insight"))

    if name and insight:
        post = Insight(name=name, book_name=book,
                       category=category, insight=insight)
        db.session.add(post)
        db.session.commit()

    return redirect(url_for("index"))


# LIKE / UNLIKE
@app.route("/like/<int:id>", methods=["POST"])
def like(id):
    post = Insight.query.get(id)
    if not post:
        return redirect(url_for("index"))

    liked = session.get("liked_posts", [])

    if id in liked:
        liked.remove(id)
        post.likes_count = max(post.likes_count - 1, 0)
    else:
        liked.append(id)
        post.likes_count += 1

    session["liked_posts"] = liked
    db.session.commit()

    return redirect(url_for("index"))


# ADMIN LOGIN
@app.route("/admin/login", methods=["GET", "POST"])
@csrf.exempt
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")


# ADMIN DASHBOARD
@app.route("/admin")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    posts = Insight.query.order_by(Insight.created_at.desc()).all()

    return render_template("admin_dashboard.html", insights=posts)

# DELETE


@app.route("/admin/delete/<int:id>", methods=["POST"])
def delete(id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    post = Insight.query.get(id)
    if post:
        db.session.delete(post)
        db.session.commit()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # use Render's assigned port
    # debug False for production
    app.run(host="0.0.0.0", port=port, debug=False)
