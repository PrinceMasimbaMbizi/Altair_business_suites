from flask import (Flask,render_template,request,redirect,url_for,flash,session,send_from_directory,abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date

import mysql.connector
import os
import requests

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")

# FLASK APP
app = Flask(__name__)

app.secret_key = "AIzaSyCzrz_RdKRGlon0Wt6ve2QHFSTJA2-IcJ0"



# COMPANY LOGO UPLOAD SETTINGS
UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "static",
    "uploads"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg"
}


def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# MONEY FORMATTER


def format_money(value):
    """
    Format money using spaces for thousands.

    Examples:
        2000       -> 2 000
        20000      -> 20 000
        200000     -> 200 000
        2450.50    -> 2 450.50
        1000000    -> 1 000 000
    """

    if value is None:
        return "0"

    try:
        value = float(value)

        # Remove unnecessary decimal .0
        if value.is_integer():
            return f"{int(value):,}".replace(",", " ")

        # Keep decimal values
        return f"{value:,.2f}".replace(",", " ")

    except (ValueError, TypeError):
        return "0"


# Make the function available inside all Jinja templates
app.jinja_env.filters["money"] = format_money


# MYSQL CONNECTION


def get_db_connection():

    return mysql.connector.connect(

        host=os.environ.get("DB_HOST"),

        port=int(
            os.environ.get(
                "DB_PORT",
                3306
            )
        ),

        user=os.environ.get("DB_USER"),

        password=os.environ.get("DB_PASSWORD"),

        database=os.environ.get("DB_NAME"),

        ssl_verify_cert=False
    )

@app.route("/company-logo")
def company_logo():

    if "user_id" not in session:
        abort(404)

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT logo
            FROM companies
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,)
        )

        company = cursor.fetchone()

        if not company or not company.get("logo"):
            abort(404)

        # Only use the filename
        # This protects against paths stored in the database.
        filename = os.path.basename(
            company["logo"]
        )

        logo_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        print("COMPANY LOGO FROM DATABASE:", company["logo"])
        print("COMPANY LOGO FILE:", logo_path)
        print("LOGO EXISTS:", os.path.isfile(logo_path))

        if not os.path.isfile(logo_path):
            abort(404)

        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            filename
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

# REGISTER


@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:

            flash(
                "Please fill in all fields.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        db = None
        cursor = None

        try:

            db = get_db_connection()

            cursor = db.cursor(
                dictionary=True
            )

            # Check existing account

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                flash(
                    "An account with this email already exists.",
                    "error"
                )

                return redirect(
                    url_for("register")
                )

            # Hash password

            password_hash = generate_password_hash(
                password
            )

            # Create user

            cursor.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password_hash
                )
                VALUES
                (
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    name,
                    email,
                    password_hash
                )
            )

            db.commit()

            flash(
                "Account created successfully. Please login.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except Exception as e:

            if db:
                db.rollback()

            print(
                "REGISTER ERROR:",
                e
            )

            flash(
                "Could not create your account.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        finally:

            if cursor:
                cursor.close()

            if db:
                db.close()

    return render_template(
        "register.html"
    )



# LOGIN


@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Please enter your email and password.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        db = None
        cursor = None

        try:

            db = get_db_connection()

            cursor = db.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s
                LIMIT 1
                """,
                (email,)
            )

            user = cursor.fetchone()

            if user and check_password_hash(
                user["password_hash"],
                password
            ):

                session["user_id"] = user["id"]

                session["user_name"] = user["name"]

                session["user_email"] = user["email"]

                flash(
                    "Welcome back!",
                    "success"
                )

                return redirect(
                    url_for("dashboard")
                )

            flash(
                "Invalid email or password.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        except Exception as e:

            print(
                "LOGIN ERROR:",
                e
            )

            flash(
                "Unable to login right now.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        finally:

            if cursor:
                cursor.close()

            if db:
                db.close()

    return render_template(
        "login.html"
    )



# LOGOUT


@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )



# COMPANY SETUP


@app.route(
    "/company-setup",
    methods=["GET", "POST"]
)
def company_setup():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    if request.method == "POST":

        company_name = request.form.get(
            "company_name",
            ""
        ).strip()

        industry = request.form.get(
            "industry",
            ""
        ).strip()

        specialization = request.form.get(
            "specialization",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        website = request.form.get(
            "website",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        city = request.form.get(
            "city",
            ""
        ).strip()

        country = request.form.get(
            "country",
            ""
        ).strip()

        services = request.form.get(
            "services",
            ""
        ).strip()

        # Validation

        if not company_name:

            flash(
                "Company name is required.",
                "error"
            )

            return redirect(
                url_for("company_setup")
            )

        if not industry:

            flash(
                "Please select your industry.",
                "error"
            )

            return redirect(
                url_for("company_setup")
            )

        if not specialization:

            flash(
                "Please enter your company specialization.",
                "error"
            )

            return redirect(
                url_for("company_setup")
            )

        if not description:

            flash(
                "Please provide a company description.",
                "error"
            )

            return redirect(
                url_for("company_setup")
            )

        if not services:

            flash(
                "Please enter your services or products.",
                "error"
            )

            return redirect(
                url_for("company_setup")
            )

        # Logo

        logo = request.files.get("logo")

        logo_filename = None

        if logo and logo.filename:

            if not allowed_file(
                logo.filename
            ):

                flash(
                    "Invalid logo format. Please use PNG, JPG or JPEG.",
                    "error"
                )

                return redirect(
                    url_for("company_setup")
                )

            original_filename = secure_filename(
                logo.filename
            )

            extension = original_filename.rsplit(
                ".",
                1
            )[1].lower()

            logo_filename = (
                f"company_{user_id}.{extension}"
            )

            os.makedirs(
                app.config["UPLOAD_FOLDER"],
                exist_ok=True
            )

            logo.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    logo_filename
                )
            )

        db = None
        cursor = None

        try:

            db = get_db_connection()

            cursor = db.cursor()

            # Prevent duplicate company profile

            cursor.execute(
                """
                SELECT id
                FROM companies
                WHERE user_id = %s
                LIMIT 1
                """,
                (user_id,)
            )

            existing_company = cursor.fetchone()

            if existing_company:

                cursor.execute(
                    """
                    UPDATE companies
                    SET
                        company_name = %s,
                        industry = %s,
                        specialization = %s,
                        description = %s,
                        phone = %s,
                        email = %s,
                        website = %s,
                        address = %s,
                        city = %s,
                        country = %s,
                        services = %s
                    WHERE user_id = %s
                    """,
                    (
                        company_name,
                        industry,
                        specialization,
                        description,
                        phone,
                        email,
                        website,
                        address,
                        city,
                        country,
                        services,
                        user_id
                    )
                )

                if logo_filename:

                    cursor.execute(
                        """
                        UPDATE companies
                        SET logo = %s
                        WHERE user_id = %s
                        """,
                        (
                            logo_filename,
                            user_id
                        )
                    )

            else:

                cursor.execute(
                    """
                    INSERT INTO companies
                    (
                        user_id,
                        company_name,
                        industry,
                        specialization,
                        description,
                        phone,
                        email,
                        website,
                        address,
                        city,
                        country,
                        services,
                        logo
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        user_id,
                        company_name,
                        industry,
                        specialization,
                        description,
                        phone,
                        email,
                        website,
                        address,
                        city,
                        country,
                        services,
                        logo_filename
                    )
                )

            db.commit()

            flash(
                "Company profile created successfully!",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        except Exception as e:

            if db:
                db.rollback()

            print(
                "COMPANY SETUP ERROR:",
                e
            )

            flash(
                "Could not save company profile.",
                "error"
            )

            return redirect(
                url_for("company_setup")
            )

        finally:

            if cursor:
                cursor.close()

            if db:
                db.close()

    return render_template(
        "company_setup.html"
    )



# DASHBOARD


@app.route("/")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM companies
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,)
        )

        company = cursor.fetchone()

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    if company is None:

        return redirect(
            url_for("company_setup")
        )

    return render_template(
        "dashboard.html",

        company=company,

        user_name=session.get(
            "user_name"
        ),

        user_email=session.get(
            "user_email"
        )
    )



# CUSTOMERS


@app.route("/customer")
def customer():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    try:

        # Company

        cursor.execute(
            """
            SELECT *
            FROM companies
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,)
        )

        company = cursor.fetchone()

        if company is None:

            return redirect(
                url_for("company_setup")
            )

        # Customers

        cursor.execute(
            """
            SELECT *
            FROM customers
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (user_id,)
        )

        customers = cursor.fetchall()

        # Total

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM customers
            WHERE user_id = %s
            """,
            (user_id,)
        )

        total_customers = cursor.fetchone()["total"]

        # New this month

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM customers
            WHERE user_id = %s
            AND MONTH(created_at) = MONTH(CURRENT_DATE())
            AND YEAR(created_at) = YEAR(CURRENT_DATE())
            """,
            (user_id,)
        )

        new_customers = cursor.fetchone()["total"]

        # Active

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM customers
            WHERE user_id = %s
            AND status = 'Active'
            """,
            (user_id,)
        )

        active_customers = cursor.fetchone()["total"]

        # Average value

        cursor.execute(
            """
            SELECT COALESCE(
                AVG(total_spent),
                0
            ) AS average_value
            FROM customers
            WHERE user_id = %s
            """,
            (user_id,)
        )

        average_value = cursor.fetchone()[
            "average_value"
        ]

        return render_template(
            "customer.html",

            company=company,

            customers=customers,

            total_customers=total_customers,

            new_customers=new_customers,

            active_customers=active_customers,

            average_value=average_value,

            user_name=session.get(
                "user_name"
            ),

            user_email=session.get(
                "user_email"
            )
        )

    finally:

        cursor.close()
        db.close()



# ADD CUSTOMER


@app.route(
    "/customer/add",
    methods=["POST"]
)
def add_customer():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    name = request.form.get(
        "name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    company_name = request.form.get(
        "company_name",
        ""
    ).strip()

    address = request.form.get(
        "address",
        ""
    ).strip()

    city = request.form.get(
        "city",
        ""
    ).strip()

    country = request.form.get(
        "country",
        ""
    ).strip()

    status = request.form.get(
        "status",
        "Active"
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    if not name:

        flash(
            "Customer name is required.",
            "error"
        )

        return redirect(
            url_for("customer")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO customers
            (
                user_id,
                name,
                email,
                phone,
                company_name,
                address,
                city,
                country,
                status,
                notes
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                user_id,
                name,
                email,
                phone,
                company_name,
                address,
                city,
                country,
                status,
                notes
            )
        )

        db.commit()

        flash(
            "Customer added successfully!",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "ERROR ADDING CUSTOMER:",
            e
        )

        flash(
            "Could not add customer.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("customer")
    )



# INVOICE PAGE


@app.route("/invoice")
def invoice():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    try:

        # Company

        cursor.execute(
            """
            SELECT *
            FROM companies
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,)
        )

        company = cursor.fetchone()

        # Invoices

        cursor.execute(
            """
            SELECT *
            FROM invoices
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (user_id,)
        )

        invoices = cursor.fetchall()

        # Statistics

        cursor.execute(
            """
            SELECT

                COUNT(*) AS total_invoices,

                COALESCE(
                    SUM(amount),
                    0
                ) AS total_amount,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'Paid'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS paid_amount,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'Pending'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS pending_amount,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'Overdue'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS overdue_amount,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'Paid'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS paid_invoices,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'Pending'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS pending_invoices,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'Overdue'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS overdue_invoices

            FROM invoices

            WHERE user_id = %s
            """,
            (user_id,)
        )

        stats = cursor.fetchone()

        return render_template(
            "invoice.html",

            company=company,

            invoices=invoices,

            total_invoices=stats[
                "total_invoices"
            ] or 0,

            total_amount=stats[
                "total_amount"
            ] or 0,

            paid_amount=stats[
                "paid_amount"
            ] or 0,

            pending_amount=stats[
                "pending_amount"
            ] or 0,

            overdue_amount=stats[
                "overdue_amount"
            ] or 0,

            paid_invoices=stats[
                "paid_invoices"
            ] or 0,

            pending_invoices=stats[
                "pending_invoices"
            ] or 0,

            overdue_invoices=stats[
                "overdue_invoices"
            ] or 0,

            user_name=session.get(
                "user_name"
            ),

            user_email=session.get(
                "user_email"
            )
        )

    finally:

        cursor.close()
        db.close()



# VIEW INVOICE


@app.route(
    "/invoice/<int:invoice_id>"
)
def view_invoice(invoice_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    try:

        cursor.execute(
            """
            SELECT *
            FROM invoices
            WHERE id = %s
            AND user_id = %s
            LIMIT 1
            """,
            (
                invoice_id,
                user_id
            )
        )

        invoice_data = cursor.fetchone()

        if invoice_data is None:

            flash(
                "Invoice not found.",
                "error"
            )

            return redirect(
                url_for("invoice")
            )

        cursor.execute(
            """
            SELECT *
            FROM companies
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,)
        )

        company = cursor.fetchone()

        return render_template(
            "invoice_view.html",

            invoice=invoice_data,

            company=company,

            user_name=session.get(
                "user_name"
            ),

            user_email=session.get(
                "user_email"
            )
        )

    finally:

        cursor.close()
        db.close()



# CREATE INVOICE


@app.route(
    "/invoice/create",
    methods=["POST"]
)
def create_invoice():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    customer_name = request.form.get(
        "customer_name",
        ""
    ).strip()

    customer_email = request.form.get(
        "customer_email",
        ""
    ).strip()

    # Your database uses item_name
    # instead of description.

    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    # Support old invoice form too.
    # If the form still sends "description",
    # use it as item_name.

    if not item_name:

        item_name = request.form.get(
            "description",
            ""
        ).strip()

    amount = request.form.get(
        "amount",
        ""
    ).strip()

    due_date = request.form.get(
        "due_date",
        ""
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    if not customer_name:

        flash(
            "Customer name is required.",
            "error"
        )

        return redirect(
            url_for("invoice")
        )

    if not item_name:

        flash(
            "Invoice item or description is required.",
            "error"
        )

        return redirect(
            url_for("invoice")
        )

    if not amount:

        flash(
            "Invoice amount is required.",
            "error"
        )

        return redirect(
            url_for("invoice")
        )

    try:

        amount_value = float(
            amount
        )

        if amount_value < 0:

            raise ValueError

    except ValueError:

        flash(
            "Please enter a valid invoice amount.",
            "error"
        )

        return redirect(
            url_for("invoice")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        # Get the highest invoice number
        # belonging to this user.

        cursor.execute(
            """
            SELECT invoice_number
            FROM invoices
            WHERE user_id = %s
            AND invoice_number LIKE 'INV-%%'
            ORDER BY id DESC
            """,
            (user_id,)
        )

        invoice_rows = cursor.fetchall()

        highest_number = 1000

        for row in invoice_rows:

            current_invoice = row[0]

            if not current_invoice:
                continue

            try:

                current_number = int(
                    current_invoice.replace(
                        "INV-",
                        ""
                    )
                )

                if current_number > highest_number:

                    highest_number = current_number

            except ValueError:

                continue

        invoice_number = (
            f"INV-{highest_number + 1}"
        )

        # Current date

        invoice_date = date.today()

        # Insert invoice using the
        # ACTUAL database column names.

        cursor.execute(
            """
            INSERT INTO invoices
            (
                user_id,
                invoice_number,
                customer_name,
                customer_email,
                item_name,
                invoice_date,
                due_date,
                amount,
                status,
                notes
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'Pending',
                %s
            )
            """,
            (
                user_id,
                invoice_number,
                customer_name,
                customer_email,
                item_name,
                invoice_date,
                due_date if due_date else None,
                amount_value,
                notes
            )
        )

        db.commit()

        flash(
            f"Invoice {invoice_number} created successfully!",
            "success"
        )

    except mysql.connector.IntegrityError as e:

        if db:
            db.rollback()

        print(
            "CREATE INVOICE INTEGRITY ERROR:",
            e
        )

        flash(
            "Invoice number already exists. Please try again.",
            "error"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "CREATE INVOICE ERROR:",
            e
        )

        flash(
            "Could not create invoice.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("invoice")
    )



# MARK INVOICE AS PAID


@app.route(
    "/invoice/<int:invoice_id>/paid",
    methods=["POST"]
)
def mark_invoice_paid(invoice_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = get_db_connection()

    cursor = db.cursor()

    try:

        cursor.execute(
            """
            UPDATE invoices

            SET status = 'Paid'

            WHERE id = %s
            AND user_id = %s
            """,
            (
                invoice_id,
                user_id
            )
        )

        db.commit()

        flash(
            "Invoice marked as paid.",
            "success"
        )

    except Exception as e:

        db.rollback()

        print(
            "MARK PAID ERROR:",
            e
        )

        flash(
            "Could not update invoice.",
            "error"
        )

    finally:

        cursor.close()
        db.close()

    return redirect(
        url_for("invoice")
    )



# DELETE INVOICE


@app.route(
    "/invoice/<int:invoice_id>/delete",
    methods=["POST"]
)
def delete_invoice(invoice_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = get_db_connection()

    cursor = db.cursor()

    try:

        cursor.execute(
            """
            DELETE FROM invoices

            WHERE id = %s
            AND user_id = %s
            """,
            (
                invoice_id,
                user_id
            )
        )

        db.commit()

        flash(
            "Invoice deleted successfully.",
            "success"
        )

    except Exception as e:

        db.rollback()

        print(
            "DELETE INVOICE ERROR:",
            e
        )

        flash(
            "Could not delete invoice.",
            "error"
        )

    finally:

        cursor.close()
        db.close()

    return redirect(
        url_for("invoice")
    )



# REMIND CUSTOMER


@app.route(
    "/invoice/<int:invoice_id>/remind",
    methods=["POST"]
)
def remind_invoice(invoice_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    try:

        cursor.execute(
            """
            SELECT
                customer_name,
                customer_email,
                invoice_number

            FROM invoices

            WHERE id = %s
            AND user_id = %s

            LIMIT 1
            """,
            (
                invoice_id,
                user_id
            )
        )

        invoice_data = cursor.fetchone()

        if not invoice_data:

            flash(
                "Invoice not found.",
                "error"
            )

            return redirect(
                url_for("invoice")
            )

        flash(
            f"Reminder prepared for {invoice_data['customer_name']}.",
            "success"
        )

        return redirect(
            url_for("invoice")
        )

    finally:

        cursor.close()
        db.close()



# EXPENSES


@app.route(
    "/expenses/add",
    methods=["POST"]
)
def add_expense():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    expense_name = request.form.get(
        "expense_name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    amount = request.form.get(
        "amount",
        "0"
    ).strip()

    expense_date = request.form.get(
        "expense_date"
    )

    payment_method = request.form.get(
        "payment_method",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    if (
        not expense_name
        or not amount
        or not expense_date
    ):

        flash(
            "Please fill in all required expense fields.",
            "error"
        )

        return redirect(
            url_for("items")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO expenses
            (
                user_id,
                expense_name,
                category,
                amount,
                expense_date,
                payment_method,
                description
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                user_id,
                expense_name,
                category,
                amount,
                expense_date,
                payment_method,
                description
            )
        )

        db.commit()

        flash(
            "Expense added successfully.",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "ADD EXPENSE ERROR:",
            e
        )

        flash(
            "Unable to add expense.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("items")
    )



# DELETE EXPENSE


@app.route(
    "/expenses/delete/<int:expense_id>",
    methods=["POST"]
)
def delete_expense(expense_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            """
            DELETE FROM expenses

            WHERE id = %s
            AND user_id = %s
            AND recurring_payment_id IS NULL
            """,
            (
                expense_id,
                user_id
            )
        )

        db.commit()

        flash(
            "Expense deleted successfully.",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "DELETE EXPENSE ERROR:",
            e
        )

        flash(
            "Unable to delete expense.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("items")
    )



# ADD INVESTMENT


@app.route(
    "/investments/add",
    methods=["POST"]
)
def add_investment():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    investment_name = request.form.get(
        "investment_name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    amount = request.form.get(
        "amount",
        "0"
    ).strip()

    investment_date = request.form.get(
        "investment_date"
    )

    expected_return = request.form.get(
        "expected_return",
        "0"
    ).strip()

    status = request.form.get(
        "status",
        "Active"
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    if (
        not investment_name
        or not amount
        or not investment_date
    ):

        flash(
            "Please fill in all required investment fields.",
            "error"
        )

        return redirect(
            url_for("items")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO investments
            (
                user_id,
                investment_name,
                category,
                amount,
                investment_date,
                expected_return,
                status,
                description
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                user_id,
                investment_name,
                category,
                amount,
                investment_date,
                expected_return,
                status,
                description
            )
        )

        db.commit()

        flash(
            "Investment added successfully.",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "ADD INVESTMENT ERROR:",
            e
        )

        flash(
            "Unable to add investment.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("items")
    )



# DELETE INVESTMENT


@app.route(
    "/investments/delete/<int:investment_id>",
    methods=["POST"]
)
def delete_investment(investment_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            """
            DELETE FROM investments

            WHERE id = %s
            AND user_id = %s
            """,
            (
                investment_id,
                user_id
            )
        )

        db.commit()

        flash(
            "Investment deleted successfully.",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "DELETE INVESTMENT ERROR:",
            e
        )

        flash(
            "Unable to delete investment.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("items")
    )



# ADD RECURRING PAYMENT


@app.route(
    "/recurring/add",
    methods=["POST"]
)
def add_recurring_payment():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    payment_name = request.form.get(
        "payment_name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    amount = request.form.get(
        "amount",
        "0"
    ).strip()

    frequency = request.form.get(
        "frequency",
        "Monthly"
    ).strip()

    start_date = request.form.get(
        "start_date"
    )

    end_date = request.form.get(
        "end_date"
    ) or None

    next_payment_date = request.form.get(
        "next_payment_date"
    )

    payment_method = request.form.get(
        "payment_method",
        ""
    ).strip()

    status = request.form.get(
        "status",
        "Active"
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    if (
        not payment_name
        or not amount
        or not start_date
        or not next_payment_date
    ):

        flash(
            "Please fill in all required recurring payment fields.",
            "error"
        )

        return redirect(
            url_for("items")
        )

    if frequency not in (
        "Monthly",
        "Weekly",
        "Yearly"
    ):

        flash(
            "Invalid recurring payment frequency.",
            "error"
        )

        return redirect(
            url_for("items")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO recurring_payments
            (
                user_id,
                payment_name,
                category,
                amount,
                frequency,
                start_date,
                end_date,
                next_payment_date,
                payment_method,
                status,
                description
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                user_id,
                payment_name,
                category,
                amount,
                frequency,
                start_date,
                end_date,
                next_payment_date,
                payment_method,
                status,
                description
            )
        )

        db.commit()

        flash(
            "Recurring payment created successfully.",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "ADD RECURRING PAYMENT ERROR:",
            e
        )

        flash(
            "Unable to create recurring payment.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("items")
    )



# DELETE RECURRING PAYMENT


@app.route(
    "/recurring/delete/<int:payment_id>",
    methods=["POST"]
)
def delete_recurring_payment(payment_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        # Delete the recurring rule.
        #
        # Historical expenses remain in the
        # expenses table because they represent
        # actual money that was already recorded.

        cursor.execute(
            """
            DELETE FROM recurring_payments

            WHERE id = %s
            AND user_id = %s
            """,
            (
                payment_id,
                user_id
            )
        )

        db.commit()

        flash(
            "Recurring payment stopped successfully.",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "DELETE RECURRING ERROR:",
            e
        )

        flash(
            "Unable to stop recurring payment.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("items")
    )



# PROCESS RECURRING PAYMENTS

#
# This function checks recurring payments every time
# the /items page is opened.
#
# Example:
#
# Rent = R5,000
# Start = 01 September
# Next payment = 01 September
#
# When the user opens Items on 26 September:
#
# 01 September -> recorded
# 01 October   -> next payment
#
# If several months have passed, every missing
# occurrence is automatically created.
#


def process_recurring_payments(
    conn,
    cursor,
    user_id
):

    today = date.today()

    cursor.execute(
        """
        SELECT *

        FROM recurring_payments

        WHERE user_id = %s

        AND status = 'Active'

        AND next_payment_date <= %s

        ORDER BY next_payment_date ASC
        """,
        (
            user_id,
            today
        )
    )

    recurring_payments = cursor.fetchall()

    for payment in recurring_payments:

        payment_id = payment["id"]

        payment_date = payment[
            "next_payment_date"
        ]

        frequency = payment[
            "frequency"
        ]

        end_date = payment[
            "end_date"
        ]

        # Protect against bad database values.

        if not payment_date:

            continue

        while payment_date <= today:

            # If the recurring payment has
            # passed its end date, complete it.

            if end_date and payment_date > end_date:

                cursor.execute(
                    """
                    UPDATE recurring_payments

                    SET
                        status = 'Completed'

                    WHERE id = %s
                    AND user_id = %s
                    """,
                    (
                        payment_id,
                        user_id
                    )
                )

                break

            # Check if this occurrence already exists.

            cursor.execute(
                """
                SELECT id

                FROM recurring_payment_records

                WHERE recurring_payment_id = %s

                AND payment_date = %s

                LIMIT 1
                """,
                (
                    payment_id,
                    payment_date
                )
            )

            existing_record = cursor.fetchone()

            # Create occurrence if it does not exist.

            if not existing_record:

                cursor.execute(
                    """
                    INSERT INTO recurring_payment_records
                    (
                        recurring_payment_id,
                        user_id,
                        payment_date,
                        amount,
                        status,
                        notes
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        'Recorded',
                        %s
                    )
                    """,
                    (
                        payment_id,
                        user_id,
                        payment_date,
                        payment["amount"],
                        "Automatically recorded recurring payment"
                    )
                )

                # Also create a money-out expense.

                cursor.execute(
                    """
                    INSERT INTO expenses
                    (
                        user_id,
                        expense_name,
                        category,
                        amount,
                        expense_date,
                        payment_method,
                        description,
                        recurring_payment_id
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        user_id,
                        payment["payment_name"],
                        payment["category"],
                        payment["amount"],
                        payment_date,
                        payment["payment_method"],
                        "Automatically recorded from recurring payment",
                        payment_id
                    )
                )

            # Move to next occurrence.

            if frequency == "Monthly":

                cursor.execute(
                    """
                    SELECT DATE_ADD(
                        %s,
                        INTERVAL 1 MONTH
                    ) AS next_date
                    """,
                    (payment_date,)
                )

                payment_date = cursor.fetchone()[
                    "next_date"
                ]

            elif frequency == "Weekly":

                cursor.execute(
                    """
                    SELECT DATE_ADD(
                        %s,
                        INTERVAL 1 WEEK
                    ) AS next_date
                    """,
                    (payment_date,)
                )

                payment_date = cursor.fetchone()[
                    "next_date"
                ]

            elif frequency == "Yearly":

                cursor.execute(
                    """
                    SELECT DATE_ADD(
                        %s,
                        INTERVAL 1 YEAR
                    ) AS next_date
                    """,
                    (payment_date,)
                )

                payment_date = cursor.fetchone()[
                    "next_date"
                ]

            else:

                # Unknown frequency.
                # Do not keep looping.

                break

        # Update next payment date.

        cursor.execute(
            """
            UPDATE recurring_payments

            SET
                next_payment_date = %s

            WHERE id = %s
            AND user_id = %s
            """,
            (
                payment_date,
                payment_id,
                user_id
            )
        )

    conn.commit()



# INVENTORY + MONEY MANAGEMENT


@app.route("/items")
def items():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        
        # COMPANY
        

        cursor.execute(
            """
            SELECT *
            FROM companies
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,)
        )

        company = cursor.fetchone()

        
        # PROCESS RECURRING PAYMENTS
        

        process_recurring_payments(
            db,
            cursor,
            user_id
        )

        
        # INVENTORY
        

        cursor.execute(
            """
            SELECT *
            FROM inventory
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        inventory = cursor.fetchall()

        
        # INVENTORY STATISTICS
        

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM inventory
            WHERE user_id = %s
            """,
            (user_id,)
        )

        total_items = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM inventory
            WHERE user_id = %s
            AND item_type = 'Product'
            """,
            (user_id,)
        )

        total_products = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM inventory
            WHERE user_id = %s
            AND item_type = 'Service'
            """,
            (user_id,)
        )

        total_services = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM inventory
            WHERE user_id = %s
            AND item_type = 'Product'
            AND quantity > 0
            AND quantity <= low_stock_level
            """,
            (user_id,)
        )

        low_stock = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM inventory
            WHERE user_id = %s
            AND item_type = 'Product'
            AND quantity <= 0
            """,
            (user_id,)
        )

        out_of_stock = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COALESCE(
                SUM(
                    quantity * cost_price
                ),
                0
            ) AS total

            FROM inventory

            WHERE user_id = %s

            AND item_type = 'Product'
            """,
            (user_id,)
        )

        inventory_value = cursor.fetchone()[
            "total"
        ]

        
        # EXPENSES
        

        cursor.execute(
            """
            SELECT *
            FROM expenses
            WHERE user_id = %s
            ORDER BY expense_date DESC, id DESC
            """,
            (user_id,)
        )

        expenses = cursor.fetchall()

        cursor.execute(
            """
            SELECT COALESCE(
                SUM(amount),
                0
            ) AS total

            FROM expenses

            WHERE user_id = %s
            """,
            (user_id,)
        )

        total_expenses = cursor.fetchone()[
            "total"
        ]

        cursor.execute(
            """
            SELECT COALESCE(
                SUM(amount),
                0
            ) AS total

            FROM expenses

            WHERE user_id = %s

            AND MONTH(expense_date) =
                MONTH(CURRENT_DATE())

            AND YEAR(expense_date) =
                YEAR(CURRENT_DATE())
            """,
            (user_id,)
        )

        month_expenses = cursor.fetchone()[
            "total"
        ]

        cursor.execute(
            """
            SELECT COUNT(*) AS total

            FROM expenses

            WHERE user_id = %s
            """,
            (user_id,)
        )

        expense_count = cursor.fetchone()[
            "total"
        ]

        
        # INVESTMENTS
        

        cursor.execute(
            """
            SELECT *
            FROM investments
            WHERE user_id = %s
            ORDER BY investment_date DESC, id DESC
            """,
            (user_id,)
        )

        investments = cursor.fetchall()

        cursor.execute(
            """
            SELECT COALESCE(
                SUM(amount),
                0
            ) AS total

            FROM investments

            WHERE user_id = %s
            """,
            (user_id,)
        )

        total_investments = cursor.fetchone()[
            "total"
        ]

        cursor.execute(
            """
            SELECT COALESCE(
                SUM(expected_return),
                0
            ) AS total

            FROM investments

            WHERE user_id = %s
            """,
            (user_id,)
        )

        expected_returns = cursor.fetchone()[
            "total"
        ]

        cursor.execute(
            """
            SELECT COUNT(*) AS total

            FROM investments

            WHERE user_id = %s
            """,
            (user_id,)
        )

        investment_count = cursor.fetchone()[
            "total"
        ]

        
        # RECURRING PAYMENTS
        

        cursor.execute(
            """
            SELECT *
            FROM recurring_payments
            WHERE user_id = %s
            ORDER BY next_payment_date ASC, id DESC
            """,
            (user_id,)
        )

        recurring_payments = cursor.fetchall()

        cursor.execute(
            """
            SELECT COUNT(*) AS total

            FROM recurring_payments

            WHERE user_id = %s

            AND status = 'Active'
            """,
            (user_id,)
        )

        recurring_count = cursor.fetchone()[
            "total"
        ]

        cursor.execute(
            """
            SELECT COALESCE(
                SUM(
                    CASE

                        WHEN frequency = 'Monthly'
                        THEN amount

                        WHEN frequency = 'Weekly'
                        THEN amount * 4.3333

                        WHEN frequency = 'Yearly'
                        THEN amount / 12

                        ELSE 0

                    END
                ),
                0
            ) AS total

            FROM recurring_payments

            WHERE user_id = %s

            AND status = 'Active'
            """,
            (user_id,)
        )

        monthly_recurring = cursor.fetchone()[
            "total"
        ]

        
        # MONEY OUT RECORDS
        

        cursor.execute(
            """
            SELECT

                id,

                'Expense' AS record_type,

                expense_name AS record_name,

                category,

                expense_date AS record_date,

                payment_method,

                amount,

                description

            FROM expenses

            WHERE user_id = %s

            UNION ALL

            SELECT

                id,

                'Investment' AS record_type,

                investment_name AS record_name,

                category,

                investment_date AS record_date,

                NULL AS payment_method,

                amount,

                description

            FROM investments

            WHERE user_id = %s

            ORDER BY record_date DESC
            """,
            (
                user_id,
                user_id
            )
        )

        money_out_records = cursor.fetchall()

        
        # TOTAL MONEY OUT
        

        cursor.execute(
            """
            SELECT

                (
                    SELECT COALESCE(
                        SUM(amount),
                        0
                    )

                    FROM expenses

                    WHERE user_id = %s
                )

                +

                (
                    SELECT COALESCE(
                        SUM(amount),
                        0
                    )

                    FROM investments

                    WHERE user_id = %s
                )

                AS total
            """,
            (
                user_id,
                user_id
            )
        )

        total_money_out = cursor.fetchone()[
            "total"
        ]

        
        # RENDER
        

        return render_template(

            "items.html",

            company=company,

            user_name=session.get(
                "user_name"
            ),

            user_email=session.get(
                "user_email"
            ),

            # Inventory

            inventory=inventory,

            total_items=total_items,

            total_products=total_products,

            total_services=total_services,

            low_stock=low_stock,

            out_of_stock=out_of_stock,

            inventory_value=inventory_value,

            # Expenses

            expenses=expenses,

            total_expenses=total_expenses,

            month_expenses=month_expenses,

            expense_count=expense_count,

            # Investments

            investments=investments,

            total_investments=total_investments,

            expected_returns=expected_returns,

            investment_count=investment_count,

            # Recurring

            recurring_payments=recurring_payments,

            recurring_count=recurring_count,

            monthly_recurring=monthly_recurring,

            # Money Out

            money_out_records=money_out_records,

            total_money_out=total_money_out
        )

    except Exception as e:

        print(
            "ITEMS PAGE ERROR:",
            e
        )

        flash(
            "Could not load inventory and money management.",
            "error"
        )

        return render_template(

            "items.html",

            company=None,

            user_name=session.get(
                "user_name"
            ),

            user_email=session.get(
                "user_email"
            ),

            inventory=[],

            total_items=0,

            total_products=0,

            total_services=0,

            low_stock=0,

            out_of_stock=0,

            inventory_value=0,

            expenses=[],

            total_expenses=0,

            month_expenses=0,

            expense_count=0,

            investments=[],

            total_investments=0,

            expected_returns=0,

            investment_count=0,

            recurring_payments=[],

            recurring_count=0,

            monthly_recurring=0,

            money_out_records=[],

            total_money_out=0
        )

    finally:

        if cursor:

            cursor.close()

        if db:

            db.close()



# ADD INVENTORY ITEM


@app.route(
    "/items/add",
    methods=["POST"]
)
def add_item():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    sku = request.form.get(
        "sku",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    item_type = request.form.get(
        "item_type",
        "Product"
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    supplier = request.form.get(
        "supplier",
        ""
    ).strip()

    quantity = request.form.get(
        "quantity",
        "0"
    ).strip()

    low_stock_level = request.form.get(
        "low_stock_level",
        "5"
    ).strip()

    cost_price = request.form.get(
        "cost_price",
        "0"
    ).strip()

    selling_price = request.form.get(
        "selling_price",
        "0"
    ).strip()

    status = request.form.get(
        "status",
        "Active"
    ).strip()

    if not item_name:

        flash(
            "Item name is required.",
            "error"
        )

        return redirect(
            url_for("items")
        )

    try:

        quantity = float(
            quantity or 0
        )

        low_stock_level = float(
            low_stock_level or 5
        )

        cost_price = float(
            cost_price or 0
        )

        selling_price = float(
            selling_price or 0
        )

    except ValueError:

        flash(
            "Please enter valid numbers.",
            "error"
        )

        return redirect(
            url_for("items")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO inventory
            (
                user_id,
                item_name,
                sku,
                category,
                item_type,
                description,
                supplier,
                quantity,
                low_stock_level,
                cost_price,
                selling_price,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                user_id,
                item_name,
                sku,
                category,
                item_type,
                description,
                supplier,
                quantity,
                low_stock_level,
                cost_price,
                selling_price,
                status
            )
        )

        db.commit()

        flash(
            f"{item_type} added successfully!",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "ADD INVENTORY ERROR:",
            e
        )

        flash(
            "Could not add inventory item.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("items")
    )



# EDIT INVENTORY ITEM


@app.route(
    "/items/edit/<int:item_id>",
    methods=["POST"]
)
def edit_item(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    sku = request.form.get(
        "sku",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    item_type = request.form.get(
        "item_type",
        "Product"
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    supplier = request.form.get(
        "supplier",
        ""
    ).strip()

    status = request.form.get(
        "status",
        "Active"
    ).strip()

    try:

        quantity = float(
            request.form.get(
                "quantity",
                0
            )
        )

        low_stock_level = float(
            request.form.get(
                "low_stock_level",
                5
            )
        )

        cost_price = float(
            request.form.get(
                "cost_price",
                0
            )
        )

        selling_price = float(
            request.form.get(
                "selling_price",
                0
            )
        )

    except ValueError:

        flash(
            "Please enter valid numbers.",
            "error"
        )

        return redirect(
            url_for("items")
        )

    if not item_name:

        flash(
            "Item name is required.",
            "error"
        )

        return redirect(
            url_for("items")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            """
            UPDATE inventory

            SET

                item_name = %s,

                sku = %s,

                category = %s,

                item_type = %s,

                description = %s,

                supplier = %s,

                quantity = %s,

                low_stock_level = %s,

                cost_price = %s,

                selling_price = %s,

                status = %s

            WHERE id = %s

            AND user_id = %s
            """,
            (
                item_name,
                sku,
                category,
                item_type,
                description,
                supplier,
                quantity,
                low_stock_level,
                cost_price,
                selling_price,
                status,
                item_id,
                user_id
            )
        )

        db.commit()

        flash(
            "Inventory item updated successfully!",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "EDIT INVENTORY ERROR:",
            e
        )

        flash(
            "Could not update inventory item.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("items")
    )



# DELETE INVENTORY ITEM


@app.route(
    "/items/delete/<int:item_id>",
    methods=["POST"]
)
def delete_item(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            """
            DELETE FROM inventory

            WHERE id = %s

            AND user_id = %s
            """,
            (
                item_id,
                user_id
            )
        )

        db.commit()

        flash(
            "Inventory item deleted successfully.",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "DELETE INVENTORY ERROR:",
            e
        )

        flash(
            "Could not delete inventory item.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("items")
    )



# SETTINGS


@app.route(
    "/settings",
    methods=["GET", "POST"]
)
def settings():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    try:

        
        # SAVE SETTINGS
        

        if request.method == "POST":

            # Company

            company_name = request.form.get(
                "company_name",
                ""
            ).strip()

            industry = request.form.get(
                "industry",
                ""
            ).strip()

            specialization = request.form.get(
                "specialization",
                ""
            ).strip()

            description = request.form.get(
                "description",
                ""
            ).strip()

            # Contact

            phone = request.form.get(
                "phone",
                ""
            ).strip()

            email = request.form.get(
                "email",
                ""
            ).strip()

            website = request.form.get(
                "website",
                ""
            ).strip()

            # Address

            address = request.form.get(
                "address",
                ""
            ).strip()

            city = request.form.get(
                "city",
                ""
            ).strip()

            country = request.form.get(
                "country",
                ""
            ).strip()

            # Services

            services = request.form.get(
                "services",
                ""
            ).strip()

            # Banking

            bank_name = request.form.get(
                "bank_name",
                ""
            ).strip()

            account_name = request.form.get(
                "account_name",
                ""
            ).strip()

            account_number = request.form.get(
                "account_number",
                ""
            ).strip()

            branch_code = request.form.get(
                "branch_code",
                ""
            ).strip()

            payment_terms = request.form.get(
                "payment_terms",
                ""
            ).strip()

            # Logo

            logo = request.files.get(
                "logo"
            )

            logo_filename = None

            if logo and logo.filename:

                if not allowed_file(
                    logo.filename
                ):

                    flash(
                        "Invalid logo format. Please use PNG, JPG or JPEG.",
                        "error"
                    )

                    return redirect(
                        url_for("settings")
                    )

                original_filename = secure_filename(
                    logo.filename
                )

                extension = original_filename.rsplit(
                    ".",
                    1
                )[1].lower()

                logo_filename = (
                    f"company_{user_id}.{extension}"
                )

                os.makedirs(
                    app.config["UPLOAD_FOLDER"],
                    exist_ok=True
                )

                logo.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        logo_filename
                    )
                )

            
            # CHECK COMPANY
            

            cursor.execute(
                """
                SELECT id, logo

                FROM companies

                WHERE user_id = %s

                LIMIT 1
                """,
                (user_id,)
            )

            existing_company = cursor.fetchone()

            
            # UPDATE
            

            if existing_company:

                if logo_filename:

                    cursor.execute(
                        """
                        UPDATE companies

                        SET

                            company_name = %s,

                            industry = %s,

                            specialization = %s,

                            description = %s,

                            phone = %s,

                            email = %s,

                            website = %s,

                            address = %s,

                            city = %s,

                            country = %s,

                            services = %s,

                            bank_name = %s,

                            account_name = %s,

                            account_number = %s,

                            branch_code = %s,

                            payment_terms = %s,

                            logo = %s

                        WHERE user_id = %s
                        """,
                        (
                            company_name,
                            industry,
                            specialization,
                            description,
                            phone,
                            email,
                            website,
                            address,
                            city,
                            country,
                            services,
                            bank_name,
                            account_name,
                            account_number,
                            branch_code,
                            payment_terms,
                            logo_filename,
                            user_id
                        )
                    )

                else:

                    cursor.execute(
                        """
                        UPDATE companies

                        SET

                            company_name = %s,

                            industry = %s,

                            specialization = %s,

                            description = %s,

                            phone = %s,

                            email = %s,

                            website = %s,

                            address = %s,

                            city = %s,

                            country = %s,

                            services = %s,

                            bank_name = %s,

                            account_name = %s,

                            account_number = %s,

                            branch_code = %s,

                            payment_terms = %s

                        WHERE user_id = %s
                        """,
                        (
                            company_name,
                            industry,
                            specialization,
                            description,
                            phone,
                            email,
                            website,
                            address,
                            city,
                            country,
                            services,
                            bank_name,
                            account_name,
                            account_number,
                            branch_code,
                            payment_terms,
                            user_id
                        )
                    )

            
            # CREATE COMPANY
            

            else:

                cursor.execute(
                    """
                    INSERT INTO companies
                    (
                        user_id,

                        company_name,

                        industry,

                        specialization,

                        description,

                        phone,

                        email,

                        website,

                        address,

                        city,

                        country,

                        services,

                        bank_name,

                        account_name,

                        account_number,

                        branch_code,

                        payment_terms,

                        logo
                    )

                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        user_id,

                        company_name,

                        industry,

                        specialization,

                        description,

                        phone,

                        email,

                        website,

                        address,

                        city,

                        country,

                        services,

                        bank_name,

                        account_name,

                        account_number,

                        branch_code,

                        payment_terms,

                        logo_filename
                    )
                )

            db.commit()

            flash(
                "Settings updated successfully!",
                "success"
            )

            return redirect(
                url_for("settings")
            )

        
        # LOAD SETTINGS
        

        cursor.execute(
            """
            SELECT *

            FROM companies

            WHERE user_id = %s

            LIMIT 1
            """,
            (user_id,)
        )

        company = cursor.fetchone()

        
        # DEFAULT COMPANY
        

        if company is None:

            company = {

                "company_name": "",

                "industry": "",

                "specialization": "",

                "description": "",

                "phone": "",

                "email": "",

                "website": "",

                "address": "",

                "city": "",

                "country": "",

                "services": "",

                "bank_name": "",

                "account_name": "",

                "account_number": "",

                "branch_code": "",

                "payment_terms": "",

                "logo": None
            }

        return render_template(

            "settings.html",

            company=company,

            user_name=session.get(
                "user_name"
            ),

            user_email=session.get(
                "user_email"
            )
        )

    except Exception as e:

        db.rollback()

        print(
            "SETTINGS ERROR:",
            e
        )

        flash(
            "Could not load or save settings.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    finally:

        cursor.close()

        db.close()


#The AI part of this application is currently under development and will be available in future updates. Stay tuned for more information and features related to AI integration in the Altair Business Suits application.



@app.route("/ai-leads")
def ai_leads():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        
        # COMPANY
        

        cursor.execute("""
            SELECT *
            FROM companies
            WHERE user_id = %s
            LIMIT 1
        """, (user_id,))

        company = cursor.fetchone()

        
        # ALL LEADS
        

        cursor.execute("""
            SELECT *
            FROM leads
            WHERE user_id = %s
            ORDER BY id DESC
        """, (user_id,))

        leads = cursor.fetchall()

        
        # STATISTICS
        

        cursor.execute("""
            SELECT
                COUNT(*) AS total_leads,

                COALESCE(
                    SUM(
                        CASE
                            WHEN lead_status = 'New'
                            THEN 1
                            ELSE 0
                        END
                    ), 0
                ) AS new_leads,

                COALESCE(
                    SUM(
                        CASE
                            WHEN lead_status = 'Contacted'
                            THEN 1
                            ELSE 0
                        END
                    ), 0
                ) AS contacted_leads,

                COALESCE(
                    SUM(
                        CASE
                            WHEN lead_status = 'Interested'
                            THEN 1
                            ELSE 0
                        END
                    ), 0
                ) AS interested_leads,

                COALESCE(
                    SUM(
                        CASE
                            WHEN lead_status = 'Converted'
                            THEN 1
                            ELSE 0
                        END
                    ), 0
                ) AS converted_leads

            FROM leads
            WHERE user_id = %s
        """, (user_id,))

        stats = cursor.fetchone()

        return render_template(
            "ai_leads.html",
            company=company,
            leads=leads,
            total_leads=stats["total_leads"],
            new_leads=stats["new_leads"],
            contacted_leads=stats["contacted_leads"],
            interested_leads=stats["interested_leads"],
            converted_leads=stats["converted_leads"],
            user_name=session.get("user_name"),
            user_email=session.get("user_email")
        )

    except Exception as e:

        print("AI LEADS ERROR:", e)

        flash(
            "Unable to load AI Lead Finder.",
            "error"
        )

        return redirect(url_for("dashboard"))

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

     
@app.route("/ai-leads/add", methods=["POST"])
def add_ai_lead():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    company_name = request.form.get(
        "company_name",
        ""
    ).strip()

    industry = request.form.get(
        "industry",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    website = request.form.get(
        "website",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    contact_person = request.form.get(
        "contact_person",
        ""
    ).strip()

    source = request.form.get(
        "source",
        "Manual"
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    if not company_name:

        flash(
            "Company name is required.",
            "error"
        )

        return redirect(url_for("ai_leads"))

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO leads
            (
                user_id,
                company_name,
                industry,
                location,
                website,
                email,
                phone,
                contact_person,
                source,
                lead_status,
                lead_score,
                notes
            )

            VALUES
            (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                'New',
                0,
                %s
            )
        """, (
            user_id,
            company_name,
            industry,
            location,
            website,
            email,
            phone,
            contact_person,
            source,
            notes
        ))

        db.commit()

        flash(
            "Lead added successfully!",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print("ADD LEAD ERROR:", e)

        flash(
            "Unable to add lead.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(url_for("ai_leads"))
@app.route(
    "/ai-leads/<int:lead_id>/status",
    methods=["POST"]
)
def update_lead_status(lead_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    status = request.form.get(
        "status",
        "New"
    ).strip()

    allowed_statuses = [
        "New",
        "Contacted",
        "Interested",
        "Converted",
        "Not Interested"
    ]

    if status not in allowed_statuses:

        flash(
            "Invalid lead status.",
            "error"
        )

        return redirect(url_for("ai_leads"))

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            UPDATE leads

            SET lead_status = %s

            WHERE id = %s
            AND user_id = %s
        """, (
            status,
            lead_id,
            user_id
        ))

        db.commit()

        flash(
            "Lead status updated.",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "UPDATE LEAD STATUS ERROR:",
            e
        )

        flash(
            "Unable to update lead.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(url_for("ai_leads"))

    #to delete the lead
@app.route(
    "/ai-leads/<int:lead_id>/delete",
    methods=["POST"]
)
def delete_ai_lead(lead_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            DELETE FROM leads

            WHERE id = %s
            AND user_id = %s
        """, (
            lead_id,
            user_id
        ))

        db.commit()

        flash(
            "Lead deleted successfully.",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "DELETE LEAD ERROR:",
            e
        )

        flash(
            "Unable to delete lead.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(url_for("ai_leads"))

@app.route("/ai-leads/search", methods=["POST"])
def search_ai_leads():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    business_type = request.form.get(
        "business_type",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    keywords = request.form.get(
        "keywords",
        ""
    ).strip()

    try:
        max_results = int(
            request.form.get(
                "max_results",
                10
            )
        )
    except ValueError:
        max_results = 10

    # Keep requests reasonable
    max_results = max(
        1,
        min(max_results, 20)
    )

    if not business_type:

        flash(
            "Please enter the type of customer you want to find.",
            "error"
        )

        return redirect(url_for("ai_leads"))

    if not location:

        flash(
            "Please enter a location.",
            "error"
        )

        return redirect(url_for("ai_leads"))

    if not GOOGLE_PLACES_API_KEY:

        flash(
            "Google Places API key is not configured.",
            "error"
        )

        return redirect(url_for("ai_leads"))

    
    # BUILD GOOGLE SEARCH QUERY
    

    search_query = business_type

    if keywords:
        search_query += " " + keywords

    search_query += " in " + location

    
    # GOOGLE PLACES API
    

    url = (
        "https://places.googleapis.com/v1/"
        "places:searchText"
    )

    headers = {

        "Content-Type":
            "application/json",

        "X-Goog-Api-Key":
            GOOGLE_PLACES_API_KEY,

        "X-Goog-FieldMask":
            ",".join([
                "places.id",
                "places.displayName",
                "places.formattedAddress",
                "places.websiteUri",
                "places.nationalPhoneNumber",
                "places.internationalPhoneNumber",
                "places.types",
                "places.businessStatus",
                "places.googleMapsUri"
            ])
    }

    payload = {

        "textQuery":
            search_query,

        "pageSize":
            min(max_results, 20)
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        print(
            "GOOGLE STATUS:",
            response.status_code
        )

        print(
            "GOOGLE RESPONSE:",
            response.text
        )

        if response.status_code != 200:

            flash(
                "Google Places search failed. "
                "Check your API key and Places API configuration.",
                "error"
            )

            return redirect(
                url_for("ai_leads")
            )

        data = response.json()

    except requests.RequestException as e:

        print(
            "GOOGLE API ERROR:",
            e
        )

        flash(
            "Unable to connect to Google Places.",
            "error"
        )

        return redirect(
            url_for("ai_leads")
        )

    
    # CONVERT GOOGLE RESULTS
    

    google_results = []

    for place in data.get("places", []):

        display_name = place.get(
            "displayName",
            {}
        )

        company_name = display_name.get(
            "text",
            "Unknown Business"
        )

        phone = (
            place.get(
                "nationalPhoneNumber"
            )
            or
            place.get(
                "internationalPhoneNumber"
            )
        )

        google_results.append({

            "google_place_id":
                place.get("id"),

            "company_name":
                company_name,

            "address":
                place.get(
                    "formattedAddress",
                    ""
                ),

            "website":
                place.get(
                    "websiteUri",
                    ""
                ),

            "phone":
                phone or "",

            "types":
                place.get(
                    "types",
                    []
                ),

            "business_status":
                place.get(
                    "businessStatus",
                    ""
                ),

            "google_maps_url":
                place.get(
                    "googleMapsUri",
                    ""
                )
        })

    
    # SEND RESULTS BACK TO PAGE
    

    return render_template(
        "ai_leads.html",

        company=get_company_for_user(
            user_id
        ),

        leads=get_leads_for_user(
            user_id
        ),

        total_leads=get_lead_count(
            user_id
        ),

        new_leads=get_lead_status_count(
            user_id,
            "New"
        ),

        contacted_leads=get_lead_status_count(
            user_id,
            "Contacted"
        ),

        interested_leads=get_lead_status_count(
            user_id,
            "Interested"
        ),

        converted_leads=get_lead_status_count(
            user_id,
            "Converted"
        ),

        google_results=google_results,

        search_performed=True,

        search_query=search_query,

        user_name=session.get(
            "user_name"
        ),

        user_email=session.get(
            "user_email"
        )
    )


def get_company_for_user(user_id):

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute("""
        SELECT *
        FROM companies
        WHERE user_id = %s
        LIMIT 1
    """, (user_id,))

    company = cursor.fetchone()

    cursor.close()
    db.close()

    return company

def get_leads_for_user(user_id):

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute("""
        SELECT *
        FROM leads
        WHERE user_id = %s
        ORDER BY id DESC
    """, (user_id,))

    leads = cursor.fetchall()

    cursor.close()
    db.close()

    return leads

def get_lead_count(user_id):

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM leads
        WHERE user_id = %s
    """, (user_id,))

    result = cursor.fetchone()

    cursor.close()
    db.close()

    return result["total"]

def get_lead_status_count(
    user_id,
    status
):

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM leads
        WHERE user_id = %s
        AND lead_status = %s
    """, (
        user_id,
        status
    ))

    result = cursor.fetchone()

    cursor.close()
    db.close()

    return result["total"]

@app.route(
    "/ai-leads/save-google",
    methods=["POST"]
)
def save_google_lead():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    company_name = request.form.get(
        "company_name",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    website = request.form.get(
        "website",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    google_place_id = request.form.get(
        "google_place_id",
        ""
    ).strip()

    if not company_name:

        flash(
            "Business name is missing.",
            "error"
        )

        return redirect(
            url_for("ai_leads")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        # ---------------------------------------------
        # CHECK FOR DUPLICATE GOOGLE LEAD
        # ---------------------------------------------

        cursor.execute("""
            SELECT id
            FROM leads
            WHERE user_id = %s
            AND google_place_id = %s
            LIMIT 1
        """, (
            user_id,
            google_place_id
        ))

        existing = cursor.fetchone()

        if existing:

            flash(
                "This business is already saved.",
                "error"
            )

            return redirect(
                url_for("ai_leads")
            )

        # ---------------------------------------------
        # SAVE
        # ---------------------------------------------

        cursor.execute("""
            INSERT INTO leads
            (
                user_id,
                company_name,
                location,
                website,
                phone,
                source,
                lead_status,
                lead_score,
                google_place_id
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                'Google',
                'New',
                0,
                %s
            )
        """, (
            user_id,
            company_name,
            location,
            website,
            phone,
            google_place_id
        ))

        db.commit()

        flash(
            "Google lead saved successfully!",
            "success"
        )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "SAVE GOOGLE LEAD ERROR:",
            e
        )

        flash(
            "Unable to save Google lead.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("ai_leads")
    )

# RUN APP
if __name__ == "__main__":

    app.run(
        debug=True
    )