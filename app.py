import os
from datetime import date
from decimal import Decimal, InvalidOperation
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "spend-smart-dev-secret-key-2026")

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
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
    }
    if include_db:
        kwargs["database"] = os.getenv("MYSQL_DATABASE", "spend_smart_db")

    ssl_ca = os.getenv("MYSQL_SSL_CA")
    if ssl_ca:
        kwargs["ssl_ca"] = ssl_ca

    return mysql.connector.connect(**kwargs)

def init_db():
    """Ensure database and tables exist according to schema.sql."""
    db_name = os.getenv("MYSQL_DATABASE", "spend_smart_db")
    with get_connection(include_db=False) as conn:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    
    with get_connection(include_db=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    amount DECIMAL(10,2) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    expense_date DATE NOT NULL,
                    description VARCHAR(255) DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_expense_date (expense_date),
                    INDEX idx_category (category)
                )
            """)
        conn.commit()

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
def dashboard():
    """Render the dashboard with total, count, average, recent entries, and category breakdown chart."""
    try:
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("""
                    SELECT 
                        COALESCE(SUM(amount), 0) AS total,
                        COUNT(*) AS count,
                        COALESCE(AVG(amount), 0) AS average
                    FROM expenses
                """)
                summary = cur.fetchone() or {"total": Decimal("0.00"), "count": 0, "average": Decimal("0.00")}

                cur.execute("""
                    SELECT id, amount, category, expense_date, description
                    FROM expenses
                    ORDER BY expense_date DESC, id DESC
                    LIMIT 8
                """)
                recent = cur.fetchall()

                cur.execute("""
                    SELECT category, SUM(amount) AS total
                    FROM expenses
                    GROUP BY category
                    ORDER BY total DESC
                """)
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
            message="Could not connect to MySQL. Check your .env settings and run database/schema.sql.",
            details=str(exc)
        ), 500

@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    """Handle adding a new expense and displaying expense history."""
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
                        cur.execute("SELECT id, amount, category, expense_date, description FROM expenses ORDER BY expense_date DESC, id DESC")
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
                        "INSERT INTO expenses (amount, category, expense_date, description) VALUES (%s, %s, %s, %s)",
                        (str(amount), category, expense_date, description)
                    )
                conn.commit()
            flash("Expense saved successfully.", "success")
            return redirect(url_for("expenses"))
        except mysql.connector.Error:
            app.logger.exception("Insert failed")
            flash("Could not save expense. Check MySQL settings.", "error")
            return redirect(url_for("expenses"))

    # GET request: load all expenses
    try:
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT id, amount, category, expense_date, description FROM expenses ORDER BY expense_date DESC, id DESC")
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
def delete_expense(expense_id):
    """Delete an expense record by its ID."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
                deleted_count = cur.rowcount
            conn.commit()

        if deleted_count > 0:
            flash("Expense deleted.", "success")
        else:
            flash("Expense not found or already deleted.", "error")
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
