import os
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import wraps
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "spend-smart-dev-secret-key-2026")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

CATEGORIES = [
    "Food",
    "Travel",
    "Shopping",
    "Bills",
    "Education",
    "Health",
    "Entertainment",
    "Other"
]

CATEGORY_PALETTE = {
    "Food": "#F28CB5",
    "Travel": "#7555D9",
    "Shopping": "#F4C66A",
    "Bills": "#F09A7E",
    "Education": "#91B8F5",
    "Health": "#6CCDB4",
    "Entertainment": "#B9A7EF",
    "Other": "#A7D98C"
}

def get_connection(include_db=True):
    """Establish and return a MySQL connection using .env configuration."""
    kwargs = {
        "host": os.getenv("MYSQL_HOST", "localhost").strip(),
        "port": int(str(os.getenv("MYSQL_PORT", "3306")).strip()),
        "user": os.getenv("MYSQL_USER", "root").strip(),
        "password": os.getenv("MYSQL_PASSWORD", "").strip(),
    }
    if include_db:
        kwargs["database"] = os.getenv("MYSQL_DATABASE", "spend_smart_db").strip()

    ssl_ca = os.getenv("MYSQL_SSL_CA")
    if ssl_ca and os.path.exists(ssl_ca.strip()):
        kwargs["ssl_ca"] = ssl_ca.strip()
        kwargs["ssl_verify_cert"] = True
    elif os.getenv("MYSQL_SSL", "").strip().lower() in ("true", "1") or (
        kwargs["host"] and kwargs["host"] not in ("localhost", "127.0.0.1")
    ):
        # Enable SSL for cloud-hosted databases such as Aiven
        kwargs["ssl_disabled"] = False
        kwargs["ssl_verify_cert"] = False

    return mysql.connector.connect(**kwargs)

_db_initialized = False

def init_db():
    """Ensure database and tables exist according to schema without deleting data."""
    global _db_initialized
    db_name = os.getenv("MYSQL_DATABASE", "spend_smart_db").strip()
    # For local databases, attempt database creation if permissions allow
    try:
        with get_connection(include_db=False) as conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    except mysql.connector.Error:
        # Cloud providers like Aiven restrict CREATE DATABASE; proceed directly to table creation in existing database
        pass
    
    with get_connection(include_db=True) as conn:
        with conn.cursor() as cur:
            # 1. Users Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    full_name VARCHAR(100) NOT NULL,
                    email VARCHAR(191) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_email (email)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 2. Expenses Table (with user_id)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    expense_date DATE NOT NULL,
                    description VARCHAR(255) DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_expense_date (expense_date),
                    INDEX idx_category (category),
                    INDEX idx_user_id (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 3. Check if user_id column exists on an existing expenses table; add safely if missing
            cur.execute("SHOW COLUMNS FROM expenses LIKE 'user_id'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE expenses ADD COLUMN user_id INT NULL AFTER id, ADD INDEX idx_user_id (user_id)")

        conn.commit()
    _db_initialized = True

@app.before_request
def ensure_db_initialized():
    """Auto-initialize database tables on first web request if not already done."""
    global _db_initialized
    if not _db_initialized and request.endpoint not in ("static", "health"):
        try:
            init_db()
        except Exception as e:
            app.logger.warning(f"Database auto-initialization deferred: {e}")

def login_required(f):
    """Decorator to protect routes requiring authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

@app.cli.command("init-db")
def init_db_cli():
    """CLI command to initialize database schema."""
    init_db()
    print("Spend Smart database initialized successfully.")

@app.template_filter("currency")
def currency_filter(val):
    """Format numbers into clean currency strings with commas and 2 decimals."""
    try:
        num = Decimal(str(val or 0))
        return f"{num:,.2f}"
    except (InvalidOperation, ValueError, TypeError):
        return "0.00"

@app.get("/")
def index():
    """Welcome / Landing page for visitors; redirects authenticated users to dashboard."""
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("welcome.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle new user registration."""
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if not full_name:
            errors.append("Please enter your full name.")
        if not email or "@" not in email or "." not in email:
            errors.append("Please enter a valid email address.")
        if not password:
            errors.append("Please enter a password.")
        elif len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        elif password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("register.html", form_data=request.form), 400

        try:
            with get_connection() as conn:
                with conn.cursor(dictionary=True) as cur:
                    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                    if cur.fetchone():
                        flash("An account with this email already exists. Please log in.", "error")
                        return render_template("register.html", form_data=request.form), 400

                    password_hash = generate_password_hash(password)
                    cur.execute(
                        "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
                        (full_name, email, password_hash)
                    )
                conn.commit()

            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))
        except mysql.connector.Error as exc:
            app.logger.exception("Registration failed")
            flash("Database error during registration. Please try again.", "error")
            return render_template("register.html", form_data=request.form), 500

    return render_template("register.html", form_data={})

@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate user and establish session."""
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    next_url = request.args.get("next") or ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("login.html", form_data=request.form), 400

        try:
            with get_connection() as conn:
                with conn.cursor(dictionary=True) as cur:
                    cur.execute("SELECT id, full_name, email, password_hash FROM users WHERE email = %s", (email,))
                    user = cur.fetchone()

            if not user or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "error")
                return render_template("login.html", form_data=request.form), 401

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["user_email"] = user["email"]

            flash(f"Welcome back, {user['full_name']}!", "success")
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("dashboard"))
        except mysql.connector.Error as exc:
            app.logger.exception("Login failed")
            flash("Could not connect to database. Please try again.", "error")
            return render_template("login.html", form_data=request.form), 500

    return render_template("login.html", form_data={})

@app.route("/logout", methods=["GET", "POST"])
def logout():
    """Clear session and log user out."""
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("index"))

@app.get("/dashboard")
@login_required
def dashboard():
    """Render the user-specific dashboard with total, count, average, recent entries, and category breakdown chart."""
    user_id = session["user_id"]
    try:
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("""
                    SELECT 
                        COALESCE(SUM(amount), 0) AS total,
                        COUNT(*) AS count,
                        COALESCE(AVG(amount), 0) AS average
                    FROM expenses
                    WHERE user_id = %s
                """, (user_id,))
                summary = cur.fetchone() or {"total": Decimal("0.00"), "count": 0, "average": Decimal("0.00")}

                cur.execute("""
                    SELECT id, amount, category, expense_date, description
                    FROM expenses
                    WHERE user_id = %s
                    ORDER BY expense_date DESC, id DESC
                    LIMIT 8
                """, (user_id,))
                recent = cur.fetchall()

                cur.execute("""
                    SELECT category, SUM(amount) AS total
                    FROM expenses
                    WHERE user_id = %s
                    GROUP BY category
                    ORDER BY total DESC
                """, (user_id,))
                grouped = cur.fetchall()

        chart_labels = [r["category"] for r in grouped]
        chart_values = [float(r["total"]) for r in grouped]
        chart_colors = [CATEGORY_PALETTE.get(r["category"], "#7555D9") for r in grouped]

        return render_template(
            "dashboard.html",
            summary=summary,
            recent=recent,
            chart_labels=chart_labels,
            chart_values=chart_values,
            chart_colors=chart_colors
        )
    except mysql.connector.Error as exc:
        app.logger.exception("Database error on dashboard")
        return render_template(
            "error.html",
            message="Could not connect to MySQL. Check your database settings.",
            details=str(exc)
        ), 500

@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    """Handle adding a new expense and displaying user-specific expense history."""
    user_id = session["user_id"]
    if request.method == "POST":
        raw_amount = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        raw_date = request.form.get("expense_date", "").strip()
        description = request.form.get("description", "").strip()[:255]

        errors = []

        # Validate amount
        if not raw_amount:
            errors.append("Please enter an expense amount.")
        else:
            try:
                amount = Decimal(raw_amount)
                if not amount.is_finite() or amount <= 0:
                    errors.append("Enter a valid amount greater than zero.")
                elif amount > Decimal("99999999.99"):
                    errors.append("Amount cannot exceed ₹99,999,999.99.")
                elif amount.as_tuple().exponent < -2:
                    errors.append("Amount cannot have more than 2 decimal places.")
            except (InvalidOperation, ValueError):
                errors.append("Enter a valid amount greater than zero.")

        # Validate category
        if not category:
            errors.append("Choose a valid category.")
        elif category not in CATEGORIES:
            errors.append("Choose a valid category.")

        # Validate date
        if not raw_date:
            errors.append("Choose a valid date.")
        else:
            try:
                expense_date = date.fromisoformat(raw_date)
                if expense_date.year < 1900 or expense_date.year > 2100:
                    errors.append("Choose a valid date between year 1900 and 2100.")
            except ValueError:
                errors.append("Choose a valid date.")

        if errors:
            for err in errors:
                flash(err, "error")

            # Preserve form inputs on validation error
            try:
                with get_connection() as conn:
                    with conn.cursor(dictionary=True) as cur:
                        cur.execute(
                            "SELECT id, amount, category, expense_date, description FROM expenses WHERE user_id = %s ORDER BY expense_date DESC, id DESC",
                            (user_id,)
                        )
                        rows = cur.fetchall()
                return render_template(
                    "expenses.html",
                    expenses=rows,
                    categories=CATEGORIES,
                    today=raw_date or date.today().isoformat(),
                    form_data=request.form
                ), 400
            except mysql.connector.Error:
                return render_template(
                    "expenses.html",
                    expenses=[],
                    categories=CATEGORIES,
                    today=date.today().isoformat(),
                    form_data=request.form
                ), 400

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO expenses (user_id, amount, category, expense_date, description) VALUES (%s, %s, %s, %s, %s)",
                        (user_id, str(amount), category, expense_date, description)
                    )
                conn.commit()
            flash("Expense saved successfully.", "success")
            return redirect(url_for("expenses"))
        except mysql.connector.Error:
            app.logger.exception("Insert failed")
            flash("Could not save expense. Check MySQL settings.", "error")
            return redirect(url_for("expenses"))

    # GET request: load user's expenses
    try:
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    "SELECT id, amount, category, expense_date, description FROM expenses WHERE user_id = %s ORDER BY expense_date DESC, id DESC",
                    (user_id,)
                )
                rows = cur.fetchall()
        return render_template(
            "expenses.html",
            expenses=rows,
            categories=CATEGORIES,
            today=date.today().isoformat(),
            form_data={}
        )
    except mysql.connector.Error as exc:
        app.logger.exception("Select failed")
        return render_template(
            "error.html",
            message="Could not load expenses. Check MySQL and schema setup.",
            details=str(exc)
        ), 500

@app.post("/expenses/<int:expense_id>/delete")
@login_required
def delete_expense(expense_id):
    """Delete an expense record belonging strictly to the logged-in user."""
    user_id = session["user_id"]
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM expenses WHERE id = %s AND user_id = %s", (expense_id, user_id))
                deleted_count = cur.rowcount
            conn.commit()

        if deleted_count > 0:
            flash("Expense deleted.", "success")
        else:
            flash("Expense not found or unauthorized.", "error")
    except mysql.connector.Error:
        app.logger.exception("Delete failed")
        flash("Could not delete expense. Check MySQL settings.", "error")

    return redirect(url_for("expenses"))

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
