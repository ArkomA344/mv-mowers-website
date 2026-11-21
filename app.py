import os, sqlite3, secrets
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "mv_mowers.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, template_folder="Templates", static_folder="Static")
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-this-secret"),
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    UPLOAD_FOLDER=UPLOAD_FOLDER,
)

SERVICES = [
    ("Firewood Delivery", "Seasonal firewood delivery. Contact us for availability, delivery area, and current pricing.", "fa-fire"),
    ("Tree Service", "Tree and property work. Contact us to discuss the job and arrange an estimate.", "fa-tree"),
    ("Tear Down", "Careful teardown and removal projects. Scope and site conditions are reviewed before work begins.", "fa-hammer"),
    ("Build Up", "Property improvement and build-up projects planned around your needs.", "fa-house"),
    ("Small Engine Repair", "Repair and troubleshooting for small engines. Tell us the equipment type and symptoms.", "fa-gears"),
]

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT,
            subject TEXT NOT NULL, message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'New',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL, caption TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, item TEXT NOT NULL, amount_cents INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)
        # Seed a non-sensitive demo gallery card; replace with real project photos in admin.
        conn.commit()

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db().execute("SELECT id,name,email,is_admin FROM users WHERE id=?", (uid,)).fetchone()

@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "business_phones": ["870-214-8085", "870-373-1869"]}

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or not user["is_admin"]:
            abort(403)
        return fn(*args, **kwargs)
    return wrapped

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    return render_template("index.html", services=SERVICES)

@app.route("/services")
def services():
    return render_template("services.html", services=SERVICES)

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    matches = [s for s in SERVICES if q.lower() in (s[0] + " " + s[1]).lower()] if q else []
    return render_template("search.html", q=q, matches=matches)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        if not all([name, email, subject, message]) or len(message) > 5000:
            flash("Please complete the required fields. Messages must be under 5,000 characters.", "danger")
        else:
            db().execute(
                "INSERT INTO messages(name,email,phone,subject,message) VALUES(?,?,?,?,?)",
                (name, email, phone, subject, message)
            )
            db().commit()
            flash("Thanks! Your message has been received.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or "@" not in email or len(password) < 10:
            flash("Enter a name, valid email, and password of at least 10 characters.", "danger")
        else:
            try:
                cur = db().execute(
                    "INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                    (name, email, generate_password_hash(password))
                )
                db().commit()
                session["user_id"] = cur.lastrowid
                return redirect(url_for("account"))
            except sqlite3.IntegrityError:
                flash("That email already has an account. Please sign in.", "warning")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("admin") if user["is_admin"] else url_for("account"))
        flash("Email or password was not recognized.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("home"))

@app.route("/account")
@login_required
def account():
    user = current_user()
    orders = db().execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
    return render_template("account.html", orders=orders)

@app.route("/gallery")
def gallery():
    photos = db().execute("SELECT * FROM gallery ORDER BY id DESC").fetchall()
    return render_template("gallery.html", photos=photos)

@app.route("/admin")
@admin_required
def admin():
    messages = db().execute("SELECT * FROM messages ORDER BY id DESC LIMIT 100").fetchall()
    photos = db().execute("SELECT * FROM gallery ORDER BY id DESC").fetchall()
    orders = db().execute("SELECT orders.*, users.name AS customer FROM orders LEFT JOIN users ON users.id=orders.user_id ORDER BY orders.id DESC LIMIT 100").fetchall()
    return render_template("admin.html", messages=messages, photos=photos, orders=orders)

@app.route("/admin/message/<int:message_id>/status", methods=["POST"])
@admin_required
def message_status(message_id):
    status = request.form.get("status", "New")
    if status not in {"New", "In progress", "Closed"}:
        abort(400)
    db().execute("UPDATE messages SET status=? WHERE id=?", (status, message_id))
    db().commit()
    return redirect(url_for("admin"))

@app.route("/admin/gallery", methods=["POST"])
@admin_required
def upload_photo():
    photo = request.files.get("photo")
    caption = request.form.get("caption", "").strip()[:160]
    if not photo or not photo.filename or not allowed_file(photo.filename):
        flash("Choose a JPG, PNG, or WEBP image.", "danger")
    else:
        filename = secrets.token_hex(12) + "_" + secure_filename(photo.filename)
        photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        db().execute("INSERT INTO gallery(filename,caption) VALUES(?,?)", (filename, caption or "MV Mowers project"))
        db().commit()
        flash("Photo added to gallery.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/gallery/<int:photo_id>/delete", methods=["POST"])
@admin_required
def delete_photo(photo_id):
    photo = db().execute("SELECT * FROM gallery WHERE id=?", (photo_id,)).fetchone()
    if photo:
        path = os.path.join(app.config["UPLOAD_FOLDER"], photo["filename"])
        if os.path.isfile(path):
            os.remove(path)
        db().execute("DELETE FROM gallery WHERE id=?", (photo_id,))
        db().commit()
    return redirect(url_for("admin"))

@app.route("/payments")
def payments():
    return render_template("payments.html", stripe_ready=bool(os.environ.get("STRIPE_SECRET_KEY")))

@app.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    # Stripe Checkout keeps card details off this server. Configure keys in .env.
    try:
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        amount = int(request.form.get("amount_cents", "0"))
        description = request.form.get("description", "MV Mowers service payment").strip()[:120]
        if amount < 100 or amount > 10000000:
            flash("Enter an amount between $1 and $100,000.", "danger")
            return redirect(url_for("payments"))
        checkout = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{"price_data": {
                "currency": "usd", "product_data": {"name": description},
                "unit_amount": amount
            }, "quantity": 1}],
            success_url=url_for("payment_success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("payments", _external=True),
            customer_email=current_user()["email"]
        )
        db().execute("INSERT INTO orders(user_id,item,amount_cents,status) VALUES(?,?,?,?)",
                     (current_user()["id"], description, amount, "Checkout started"))
        db().commit()
        return redirect(checkout.url, code=303)
    except (KeyError, ImportError):
        flash("Online checkout is not configured yet. Add Stripe test keys to your environment.", "warning")
        return redirect(url_for("payments"))

@app.route("/payment-success")
@login_required
def payment_success():
    session_id = request.args.get("session_id")
    if not session_id:
        abort(400)
    try:
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        checkout = stripe.checkout.Session.retrieve(session_id)
        if checkout.payment_status == "paid":
            db().execute(
                "UPDATE orders SET status='Paid' WHERE user_id=? AND status='Checkout started' ORDER BY id DESC LIMIT 1",
                (current_user()["id"],)
            )
            db().commit()
            flash("Payment confirmed. Thank you!", "success")
        else:
            flash("Payment is still processing.", "warning")
    except Exception:
        flash("We could not verify the payment. Please contact MV Mowers before retrying.", "warning")
    return redirect(url_for("account"))

@app.errorhandler(403)
def forbidden(_error):
    return render_template("403.html"), 403

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
