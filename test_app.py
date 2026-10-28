import os
import unittest
from decimal import Decimal
from datetime import date
from app import app, get_connection, CATEGORIES

class SpendSmartTestCase(unittest.TestCase):
    def setUp(self):
        """Set up Flask test client and ensure test database has a clean expenses table."""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Clean the expenses table before each test
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE expenses")
            conn.commit()

    def tearDown(self):
        """Clean up after each test."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE expenses")
            conn.commit()

    def test_empty_dashboard(self):
        """Requirement 1 & 6: Empty dashboard displays 0 values and clean empty states."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        
        # Check summary cards display ₹0.00 and 0 entries
        self.assertIn("₹0.00", html)
        self.assertIn("0", html)
        
        # Check empty states (no fake or mockup data displayed)
        self.assertIn("Your chart starts here", html)
        self.assertIn("No expenses yet", html)

    def test_empty_expense_history(self):
        """Requirement 3 & 6: Empty expense history displays empty state message."""
        resp = self.client.get("/expenses")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("Your first expense goes here", html)
        self.assertIn("0 entries", html)

    def test_validation_amount_negative_or_zero(self):
        """Requirement 5: Rejects zero and negative amounts with a helpful message."""
        # Zero amount
        resp1 = self.client.post("/expenses", data={
            "amount": "0.00",
            "category": "Food",
            "expense_date": date.today().isoformat(),
            "description": "Free item"
        }, follow_redirects=True)
        self.assertIn("Enter a valid amount greater than zero.", resp1.data.decode("utf-8"))

        # Negative amount
        resp2 = self.client.post("/expenses", data={
            "amount": "-50.00",
            "category": "Food",
            "expense_date": date.today().isoformat(),
            "description": "Negative value"
        }, follow_redirects=True)
        self.assertIn("Enter a valid amount greater than zero.", resp2.data.decode("utf-8"))

    def test_validation_amount_non_numeric(self):
        """Requirement 5: Rejects non-numeric amounts."""
        resp = self.client.post("/expenses", data={
            "amount": "abc",
            "category": "Food",
            "expense_date": date.today().isoformat(),
            "description": "Invalid number"
        }, follow_redirects=True)
        self.assertIn("Enter a valid amount greater than zero.", resp.data.decode("utf-8"))

    def test_validation_amount_overflow(self):
        """Requirement 5: Rejects amount exceeding maximum boundary."""
        resp = self.client.post("/expenses", data={
            "amount": "100000000.00",
            "category": "Food",
            "expense_date": date.today().isoformat(),
            "description": "Too large"
        }, follow_redirects=True)
        self.assertIn("Amount cannot exceed ₹99,999,999.99.", resp.data.decode("utf-8"))

    def test_validation_invalid_category(self):
        """Requirement 5: Rejects categories not in predefined list."""
        resp = self.client.post("/expenses", data={
            "amount": "250.00",
            "category": "Cryptocurrency",
            "expense_date": date.today().isoformat(),
            "description": "Unlisted category"
        }, follow_redirects=True)
        self.assertIn("Choose a valid category.", resp.data.decode("utf-8"))

    def test_validation_invalid_date(self):
        """Requirement 5: Rejects malformed dates."""
        resp = self.client.post("/expenses", data={
            "amount": "150.00",
            "category": "Food",
            "expense_date": "not-a-valid-date",
            "description": "Bad date"
        }, follow_redirects=True)
        self.assertIn("Choose a valid date.", resp.data.decode("utf-8"))

    def test_form_preserves_input_on_validation_error(self):
        """Requirement 5: Form keeps previously entered values on validation failure."""
        resp = self.client.post("/expenses", data={
            "amount": "-5.00",
            "category": "Shopping",
            "expense_date": "2026-10-25",
            "description": "Draft shopping note"
        })
        self.assertEqual(resp.status_code, 400)
        html = resp.data.decode("utf-8")
        self.assertIn("Draft shopping note", html)
        self.assertIn("Shopping", html)

    def test_add_and_view_expense(self):
        """Requirement 2 & 3: Add expense and verify it is stored in MySQL and shown in history."""
        post_resp = self.client.post("/expenses", data={
            "amount": "450.75",
            "category": "Food",
            "expense_date": "2026-10-20",
            "description": "Team lunch"
        }, follow_redirects=True)
        
        self.assertEqual(post_resp.status_code, 200)
        html = post_resp.data.decode("utf-8")
        self.assertIn("Expense saved successfully.", html)
        self.assertIn("₹450.75", html)
        self.assertIn("Food", html)
        self.assertIn("Team lunch", html)

        # Verify record exists in MySQL database
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT * FROM expenses WHERE description = 'Team lunch'")
                row = cur.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["amount"], Decimal("450.75"))
                self.assertEqual(row["category"], "Food")
                self.assertEqual(str(row["expense_date"]), "2026-10-20")

    def test_dashboard_live_analytics(self):
        """Requirement 1 & 9: Verify total, count, average and category breakdown reflect live database data."""
        # Insert 3 expenses across 2 categories
        expenses_data = [
            ("500.00", "Food", "2026-10-21", "Groceries"),
            ("300.00", "Food", "2026-10-22", "Dinner"),
            ("200.00", "Travel", "2026-10-23", "Fuel")
        ]
        for amt, cat, dt, desc in expenses_data:
            self.client.post("/expenses", data={
                "amount": amt,
                "category": cat,
                "expense_date": dt,
                "description": desc
            })

        dash_resp = self.client.get("/")
        self.assertEqual(dash_resp.status_code, 200)
        html = dash_resp.data.decode("utf-8")

        # Total: 500 + 300 + 200 = 1,000.00
        self.assertIn("₹1,000.00", html)
        # Count: 3
        self.assertIn("3", html)
        # Average: 1000 / 3 = 333.33
        self.assertIn("₹333.33", html)
        # Recent items listed
        self.assertIn("Groceries", html)
        self.assertIn("Dinner", html)
        self.assertIn("Fuel", html)
        # Chart canvas present
        self.assertIn('id="chart"', html)

    def test_delete_expense(self):
        """Requirement 4: Deleting an expense removes it from MySQL and refreshes history."""
        # Add an expense to delete
        self.client.post("/expenses", data={
            "amount": "120.00",
            "category": "Entertainment",
            "expense_date": "2026-10-24",
            "description": "Cinema ticket"
        })

        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT id FROM expenses WHERE description = 'Cinema ticket'")
                row = cur.fetchone()
                expense_id = row["id"]

        # Delete the expense
        del_resp = self.client.post(f"/expenses/{expense_id}/delete", follow_redirects=True)
        self.assertEqual(del_resp.status_code, 200)
        html = del_resp.data.decode("utf-8")
        self.assertIn("Expense deleted.", html)
        self.assertNotIn("Cinema ticket", html)

        # Confirm deleted from MySQL
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,))
                self.assertIsNone(cur.fetchone())

    def test_delete_nonexistent_expense(self):
        """Requirement 4 & 5: Attempting to delete a nonexistent expense shows informative feedback."""
        del_resp = self.client.post("/expenses/999999/delete", follow_redirects=True)
        self.assertEqual(del_resp.status_code, 200)
        self.assertIn("Expense not found or already deleted.", del_resp.data.decode("utf-8"))

    def test_health_check(self):
        """Verify the health endpoint."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"status": "ok"})

if __name__ == "__main__":
    unittest.main()
