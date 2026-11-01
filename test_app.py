import os
import unittest
from decimal import Decimal
from datetime import date
from app import app, get_connection, init_db, CATEGORIES

class SpendSmartAuthTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure local database tables exist."""
        init_db()

    def setUp(self):
        """Set up Flask test client and clean local test tables."""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SET FOREIGN_KEY_CHECKS = 0")
                cur.execute("TRUNCATE TABLE expenses")
                cur.execute("TRUNCATE TABLE users")
                cur.execute("SET FOREIGN_KEY_CHECKS = 1")
            conn.commit()

    def tearDown(self):
        """Clean up local test tables after each test."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SET FOREIGN_KEY_CHECKS = 0")
                cur.execute("TRUNCATE TABLE expenses")
                cur.execute("TRUNCATE TABLE users")
                cur.execute("SET FOREIGN_KEY_CHECKS = 1")
            conn.commit()

    def register_user(self, full_name="Satya Manasa", email="satya@example.com", password="password123"):
        """Helper to register a user."""
        return self.client.post("/register", data={
            "full_name": full_name,
            "email": email,
            "password": password,
            "confirm_password": password
        }, follow_redirects=True)

    def login_user(self, email="satya@example.com", password="password123"):
        """Helper to log in a user."""
        return self.client.post("/login", data={
            "email": email,
            "password": password
        }, follow_redirects=True)

    def test_welcome_page_unauthenticated(self):
        """Requirement 1: Unauthenticated visitor sees the Welcome / Landing page."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("Make every rupee", html)
        self.assertIn("Log In", html)
        self.assertIn("Create Account", html)

    def test_user_registration_success(self):
        """Requirement 2: New user can register successfully."""
        resp = self.register_user("Alice Wonderland", "alice@example.com", "securepass1")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("Account created successfully! Please log in.", html)
        self.assertIn("Welcome back", html)

    def test_registration_duplicate_email_rejected(self):
        """Requirement 2: Duplicate email registration is blocked."""
        self.register_user("Alice Wonderland", "alice@example.com", "securepass1")
        resp = self.register_user("Alice Clone", "alice@example.com", "differentpass")
        self.assertEqual(resp.status_code, 400)
        html = resp.data.decode("utf-8")
        self.assertIn("An account with this email already exists", html)

    def test_registration_validation(self):
        """Requirement 2: Form validation for passwords and empty fields."""
        # Short password
        resp = self.client.post("/register", data={
            "full_name": "Bob",
            "email": "bob@example.com",
            "password": "123",
            "confirm_password": "123"
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Password must be at least 6 characters long.", resp.data.decode("utf-8"))

        # Password mismatch
        resp2 = self.client.post("/register", data={
            "full_name": "Bob",
            "email": "bob@example.com",
            "password": "password123",
            "confirm_password": "password456"
        })
        self.assertEqual(resp2.status_code, 400)
        self.assertIn("Passwords do not match.", resp2.data.decode("utf-8"))

    def test_user_login_success(self):
        """Requirement 3: Registered user can log in and reach dashboard."""
        self.register_user("Charlie Brown", "charlie@example.com", "mypassword")
        resp = self.login_user("charlie@example.com", "mypassword")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("Welcome back, Charlie Brown!", html)
        self.assertIn("Your spending overview", html)

    def test_login_invalid_password(self):
        """Requirement 3: Incorrect password is rejected."""
        self.register_user("Charlie Brown", "charlie@example.com", "mypassword")
        resp = self.login_user("charlie@example.com", "wrongpassword")
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid email or password.", resp.data.decode("utf-8"))

    def test_unauthenticated_protected_routes(self):
        """Requirement 3: Unauthenticated access to dashboard and expenses is redirected to login."""
        dash_resp = self.client.get("/dashboard", follow_redirects=True)
        self.assertIn("Please log in to access this page.", dash_resp.data.decode("utf-8"))
        self.assertIn("Log In", dash_resp.data.decode("utf-8"))

        exp_resp = self.client.get("/expenses", follow_redirects=True)
        self.assertIn("Please log in to access this page.", exp_resp.data.decode("utf-8"))

    def test_add_and_view_expense(self):
        """Requirement 5 & 7: Logged-in user can add and view expenses."""
        self.register_user("User One", "user1@example.com", "pass123")
        self.login_user("user1@example.com", "pass123")

        post_resp = self.client.post("/expenses", data={
            "amount": "450.75",
            "category": "Food",
            "expense_date": "2026-11-01",
            "description": "Lunch meeting"
        }, follow_redirects=True)
        self.assertEqual(post_resp.status_code, 200)
        html = post_resp.data.decode("utf-8")
        self.assertIn("Expense saved successfully.", html)
        self.assertIn("₹450.75", html)
        self.assertIn("Lunch meeting", html)

    def test_multi_user_expense_isolation(self):
        """Requirement 5 & 10: User B cannot see or delete User A's expenses."""
        # 1. User A registers and adds an expense of ₹1,000.00
        self.register_user("User A", "usera@example.com", "pass1234")
        self.login_user("usera@example.com", "pass1234")
        self.client.post("/expenses", data={
            "amount": "1000.00",
            "category": "Food",
            "expense_date": "2026-11-01",
            "description": "Secret Dinner A"
        })

        # Retrieve User A's expense ID
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT id FROM expenses WHERE description = 'Secret Dinner A'")
                user_a_expense_id = cur.fetchone()["id"]

        # User A logs out
        self.client.get("/logout")

        # 2. User B registers and logs in
        self.register_user("User B", "userb@example.com", "pass1234")
        self.login_user("userb@example.com", "pass1234")

        # User B views dashboard: must be ₹0.00 and 0 entries
        dash_b = self.client.get("/dashboard")
        self.assertEqual(dash_b.status_code, 200)
        dash_html = dash_b.data.decode("utf-8")
        self.assertIn("₹0.00", dash_html)
        self.assertIn("0", dash_html)
        self.assertNotIn("Secret Dinner A", dash_html)

        # User B views expenses list: must NOT see User A's expense
        exp_b = self.client.get("/expenses")
        self.assertNotIn("Secret Dinner A", exp_b.data.decode("utf-8"))
        self.assertNotIn("₹1,000.00", exp_b.data.decode("utf-8"))

        # User B attempts to DELETE User A's expense ID
        del_attempt = self.client.post(f"/expenses/{user_a_expense_id}/delete", follow_redirects=True)
        self.assertEqual(del_attempt.status_code, 200)
        self.assertIn("Expense not found or unauthorized.", del_attempt.data.decode("utf-8"))

        # Confirm User A's expense is still alive in the database
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT * FROM expenses WHERE id = %s", (user_a_expense_id,))
                self.assertIsNotNone(cur.fetchone())

    def test_dashboard_calculations_user_specific(self):
        """Requirement 5 & 9: Calculations are strictly user-specific."""
        # User 1 has ₹500
        self.register_user("User 1", "u1@example.com", "pass123")
        self.login_user("u1@example.com", "pass123")
        self.client.post("/expenses", data={
            "amount": "500.00", "category": "Food", "expense_date": "2026-11-01", "description": "Groceries"
        })
        self.client.get("/logout")

        # User 2 has ₹200
        self.register_user("User 2", "u2@example.com", "pass123")
        self.login_user("u2@example.com", "pass123")
        self.client.post("/expenses", data={
            "amount": "200.00", "category": "Travel", "expense_date": "2026-11-01", "description": "Taxi"
        })

        # User 2 dashboard shows only ₹200.00, count 1
        dash = self.client.get("/dashboard")
        html = dash.data.decode("utf-8")
        self.assertIn("₹200.00", html)
        self.assertIn("1", html)
        self.assertNotIn("₹500.00", html)

    def test_logout(self):
        """Requirement 10: Logout works and locks protected routes."""
        self.register_user("Logged User", "logged@example.com", "pass123")
        self.login_user("logged@example.com", "pass123")

        logout_resp = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(logout_resp.status_code, 200)
        self.assertIn("You have been logged out successfully.", logout_resp.data.decode("utf-8"))

        # Protected route redirects to login
        dash_resp = self.client.get("/dashboard", follow_redirects=True)
        self.assertIn("Please log in to access this page.", dash_resp.data.decode("utf-8"))

    def test_health_check(self):
        """Verify health check endpoint remains accessible."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"status": "ok"})

if __name__ == "__main__":
    unittest.main()
