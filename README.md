# Spend Smart — Personal Expense Tracking and Analysis System

Spend Smart is a web-based personal finance and expense analysis system built with **Python**, **Flask**, **MySQL**, **HTML5/CSS3**, and **Chart.js**. It features a modern, lively palette (deep navy, lavender/purple, rose pink, mint teal, and cream) with responsive rounded card components.

---

## Features

1. **Interactive Dashboard**:
   - **Total Expenses**: Real-time sum across all recorded expenses with currency formatting (`₹`).
   - **Entry Count**: Total number of transactions tracked.
   - **Average Expense**: Automatic per-entry average calculation.
   - **Category-wise Spending Breakdown**: Interactive Chart.js doughnut chart with custom category colors and formatted currency tooltips.
   - **Recent Activity**: Quick snapshot of latest expenses displaying category avatar badges, dates, optional descriptions, and amounts.
   - **Clean Zero States**: Friendly guidance when no records are present (no simulated/mock data pretending to be live).

2. **Expense Management**:
   - **Add Expense**: Form capturing Amount (₹), Category, Expense Date, and optional Description.
   - **Input Validation**: Robust server-side validation ensuring positive finite amounts (up to ₹99,999,999.99 with up to 2 decimal places), valid category selections, and proper dates.
   - **Form State Preservation**: Entered values are preserved in the form if validation detects an error, preventing lost input.
   - **Expense History**: Chronological table showing category badges, dates, descriptions, formatted amounts, and deletion controls.
   - **Delete Expense**: One-click record deletion with browser confirmation dialog and feedback messages.

3. **Database & Security**:
   - Parameterized SQL queries preventing SQL injection vulnerabilities.
   - Environment-variable-based credentials (`.env` based on `.env.example`).
   - No hard-coded database passwords in repository files.
   - Built-in database initialization CLI (`flask init-db`) alongside `database/schema.sql`.

---

## Tech Stack

- **Backend**: Python 3, Flask 3.x
- **Database**: MySQL 8.x (`mysql-connector-python`)
- **Frontend**: Semantic HTML5, Vanilla CSS3 (Custom Responsive Design), Chart.js
- **Environment Management**: `python-dotenv`

---

## Project Structure

```text
Spend_Smart_Antigravity_Package/
│
├── .env.example               # Template for environment configuration
├── .env                       # Local environment variables (git-ignored)
├── .gitignore                 # Excludes .env, virtual environments, and caches
├── requirements.txt           # Python dependencies
├── app.py                     # Main Flask application and route controllers
├── test_app.py                # Automated test suite (13 test cases)
├── README.md                  # Project setup and documentation
│
├── database/
│   └── schema.sql             # SQL script to create database and tables
│
├── docs/
│   └── ANTIGRAVITY_PROMPT.md  # Project specification & requirements
│
├── static/
│   └── css/
│       └── style.css          # Responsive styling (navy, purple, pink, mint, cream)
│
└── templates/
    ├── base.html              # Layout shell, sidebar, topbar, and flash messages
    ├── dashboard.html         # Overview dashboard, KPI cards, Chart.js doughnut
    ├── expenses.html          # Add expense form and expense history table
    └── error.html             # Diagnostic page for database setup / connection issues
```

---

## Setup & Installation

### 1. Prerequisites
- Python 3.10+ installed
- MySQL Server 8.0+ installed and running locally
- Git (optional)

### 2. Set Up Virtual Environment
Open PowerShell or your preferred terminal in the project directory:

```powershell
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows Command Prompt:
.\.venv\Scripts\activate.bat
# macOS / Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Database Credentials (.env)
Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set your MySQL credentials (never commit this file):

```env
FLASK_SECRET_KEY=your-random-secret-key
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=spend_smart_db
```

### 5. Initialize the MySQL Database
You can initialize the database using either method below:

**Method A: Using Flask CLI (Recommended)**
```powershell
flask init-db
```

**Method B: Using MySQL Workbench or MySQL CLI**
Open and run `database/schema.sql` in MySQL Workbench, or run:
```powershell
mysql -u root -p < database/schema.sql
```

### 6. Run the Application
```powershell
python app.py
```

The application will start on `http://127.0.0.1:5000`. Open this URL in your web browser.

---

## Running the Automated Test Suite

The test suite in `test_app.py` verifies all core requirements:
- Empty dashboard rendering and zero-states
- Form input validation (negative amounts, non-numeric values, overflow amounts, invalid categories, invalid dates)
- Form input draft preservation on error
- Adding expenses and verifying persistence in MySQL
- Dashboard live calculation (total sum, count, average, category breakdown, recent items)
- Expense deletion and deleted row verification
- Attempted deletion of non-existent IDs
- Health check endpoint

To run the tests:

```powershell
python test_app.py
```

Expected output:
```text
Ran 13 tests in ~4s

OK
```

---

## Summary of Changes and Refinements

1. **Architecture & Database Initialization**:
   - Added `init_db()` and `@app.cli.command("init-db")` in `app.py` for automated schema creation.
   - Connected application to MySQL database `spend_smart_db` with parameterized queries.

2. **Dashboard Refinement**:
   - Connected live MySQL aggregation queries for total spending, entry count, and average expense.
   - Added custom Jinja currency filter (`currency`) supporting Indian Rupee (`₹`) notation with commas and 2 decimals.
   - Enhanced Chart.js doughnut chart with responsive sizing, 8-color category palette, and rupee-formatted hover tooltips.
   - Maintained clean zero-states when the database is empty without displaying synthetic mockup data.

3. **Expense Form & Validation**:
   - Implemented strict server-side validation for amounts (finite, `> 0`, `<= 99999999.99`, max 2 decimals), categories (must match predefined list), and dates (valid ISO format).
   - Added input preservation on validation failure (`form_data` rendered in form fields) so users do not lose typed descriptions or amounts.

4. **Expense History & Deletion**:
   - Formatted table with category-specific tags, clean dates, descriptions (with `—` fallback for empty fields), and formatted amounts.
   - Added confirmation dialog on deletion with friendly success/error flash notifications.
   - Checked `cur.rowcount` to distinguish between successfully deleted rows and non-existent IDs.

5. **Design & Code Quality**:
   - Re-formatted and organized all minified HTML/CSS files into readable, well-structured files.
   - Added category avatar and tag color schemes (`.tag-food`, `.tag-travel`, `.tag-shopping`, etc.) matching the lively navy, purple, pink, mint, and cream palette.
   - Added responsive table scrolling and mobile adaptations.
   - Created a comprehensive test suite `test_app.py` with 13 automated tests.
