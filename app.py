from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "altair-secret-key"

# COMPANY LOGO UPLOAD SETTINGS

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# MYSQL CONNECTION

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        ssl_verify_cert=False
    )


# REGISTER

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not name or not email or not password:

            flash("Please fill in all fields.", "error")

            return redirect(url_for("register"))

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Check if email already exists
        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            db.close()

            flash("An account with this email already exists.", "error")

            return redirect(url_for("register"))

        # Hash password
        password_hash = generate_password_hash(password)

        # Create user
        cursor.execute("""
            INSERT INTO users
            (name, email, password_hash)
            VALUES (%s, %s, %s)
        """, (
            name,
            email,
            password_hash
        ))

        db.commit()

        cursor.close()
        db.close()

        flash("Account created successfully. Please login.", "success")

        return redirect(url_for("login"))

    return render_template("register.html")


# LOGIN

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:

            flash("Please enter your email and password.", "error")

            return redirect(url_for("login"))

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM users
            WHERE email = %s
        """, (email,))

        user = cursor.fetchone()

        cursor.close()
        db.close()

        # Check user and password
        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]

            flash("Welcome back!", "success")

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

        return redirect(url_for("login"))

    return render_template("login.html")


# LOGOUT

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "success")

    return redirect(url_for("login"))


# For company setup

@app.route("/company-setup", methods=["GET", "POST"])
def company_setup():

    # User must be logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]


   
    # FORM SUBMITTED

    if request.method == "POST":

        company_name = request.form.get("company_name")
        industry = request.form.get("industry")
        specialization = request.form.get("specialization")
        description = request.form.get("description")

        phone = request.form.get("phone")
        email = request.form.get("email")
        website = request.form.get("website")

        address = request.form.get("address")
        city = request.form.get("city")
        country = request.form.get("country")

        services = request.form.get("services")
       
        # VALIDATION

        if not company_name:
            flash("Company name is required.", "error")
            return redirect(url_for("company_setup"))

        if not industry:
            flash("Please select your industry.", "error")
            return redirect(url_for("company_setup"))

        if not specialization:
            flash("Please enter your company specialization.", "error")
            return redirect(url_for("company_setup"))

        if not description:
            flash("Please provide a company description.", "error")
            return redirect(url_for("company_setup"))

        if not services:
            flash("Please enter your services or products.", "error")
            return redirect(url_for("company_setup"))

        # HANDLE LOGO

        logo = request.files.get("logo")

        logo_filename = None

        if logo and logo.filename:

            if not allowed_file(logo.filename):

                flash(
                    "Invalid logo format. Please use PNG, JPG or JPEG.",
                    "error"
                )

                return redirect(url_for("company_setup"))


            original_filename = secure_filename(logo.filename)

            # for user ID so different companies
            

            extension = original_filename.rsplit(".", 1)[1].lower()

            logo_filename = f"company_{user_id}.{extension}"


            # Make sure upload folder exists

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


        # SAVE COMPANY TO DATABASE

        db = get_db_connection()

        cursor = db.cursor()


        cursor.execute("""
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
        """, (
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
        ))


        db.commit()

        cursor.close()
        db.close()


        # SUCCESS

        flash(
            "Company profile created successfully!",
            "success"
        )

        return redirect(url_for("dashboard"))


    
    # SHOW FORM

    return render_template("company_setup.html")


# DASHBOARD

@app.route("/")
def dashboard():

    # Make sure the user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Get the company belonging to the logged-in user
    cursor.execute("""
        SELECT *
        FROM companies
        WHERE user_id = %s
        LIMIT 1
    """, (user_id,))

    company = cursor.fetchone()

    cursor.close()
    db.close()

    # If the user has not completed company setup
    if company is None:
        return redirect(url_for("company_setup"))

    return render_template(
        "dashboard.html",
        company=company,
        user_name=session["user_name"],
        user_email=session["user_email"]
    )


# CUSTOMER
@app.route("/customer")
def customer():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

  
    # GET COMPANY
  

    cursor.execute("""
        SELECT *
        FROM companies
        WHERE user_id = %s
        LIMIT 1
    """, (user_id,))

    company = cursor.fetchone()

    if company is None:

        cursor.close()
        db.close()

        return redirect(url_for("company_setup"))


  
    # GET CUSTOMERS
  

    cursor.execute("""
        SELECT *
        FROM customers
        WHERE user_id = %s
        ORDER BY id DESC
    """, (user_id,))

    customers = cursor.fetchall()


  
    # TOTAL CUSTOMERS
  

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM customers
        WHERE user_id = %s
    """, (user_id,))

    total_customers = cursor.fetchone()["total"]


  
    # NEW CUSTOMERS THIS MONTH
  

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM customers
        WHERE user_id = %s
        AND MONTH(created_at) = MONTH(CURRENT_DATE())
        AND YEAR(created_at) = YEAR(CURRENT_DATE())
    """, (user_id,))

    new_customers = cursor.fetchone()["total"]


  
    # ACTIVE CUSTOMERS
  

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM customers
        WHERE user_id = %s
        AND status = 'Active'
    """, (user_id,))

    active_customers = cursor.fetchone()["total"]


  
    # AVERAGE CUSTOMER VALUE
  

    cursor.execute("""
        SELECT COALESCE(AVG(total_spent), 0) AS average_value
        FROM customers
        WHERE user_id = %s
    """, (user_id,))

    average_value = cursor.fetchone()["average_value"]


    cursor.close()
    db.close()


    return render_template(
        "customer.html",

        company=company,

        customers=customers,

        total_customers=total_customers,

        new_customers=new_customers,

        active_customers=active_customers,

        average_value=average_value,

        user_name=session["user_name"],

        user_email=session["user_email"]
    )


@app.route("/customer/add", methods=["POST"])
def add_customer():

    # Make sure user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Get form data
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    company_name = request.form.get("company_name", "").strip()
    address = request.form.get("address", "").strip()
    city = request.form.get("city", "").strip()
    country = request.form.get("country", "").strip()
    status = request.form.get("status", "Active").strip()
    notes = request.form.get("notes", "").strip()

    # Validate customer name
    if not name:
        flash("Customer name is required.", "error")
        return redirect(url_for("customer"))

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
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
        ))

        db.commit()

        cursor.close()
        db.close()

        flash("Customer added successfully!", "success")

    except Exception as e:

        print("ERROR ADDING CUSTOMER:", e)

        flash("Could not add customer.", "error")

    return redirect(url_for("customer"))



# INVOICE PAGE



# APP.PY — INVOICE ROUTES


@app.route("/invoice")
def invoice():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

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

    # INVOICES
    cursor.execute("""
        SELECT *
        FROM invoices
        WHERE user_id = %s
        ORDER BY id DESC
    """, (user_id,))
    invoices = cursor.fetchall()

    # STATS
    cursor.execute("""
        SELECT
            COUNT(*) AS total_invoices,

            COALESCE(SUM(amount), 0) AS total_amount,

            COALESCE(
                SUM(
                    CASE
                        WHEN status = 'Paid'
                        THEN amount
                        ELSE 0
                    END
                ), 0
            ) AS paid_amount,

            COALESCE(
                SUM(
                    CASE
                        WHEN status = 'Pending'
                        THEN amount
                        ELSE 0
                    END
                ), 0
            ) AS pending_amount,

            COALESCE(
                SUM(
                    CASE
                        WHEN status = 'Overdue'
                        THEN amount
                        ELSE 0
                    END
                ), 0
            ) AS overdue_amount,

            SUM(
                CASE
                    WHEN status = 'Paid'
                    THEN 1
                    ELSE 0
                END
            ) AS paid_invoices,

            SUM(
                CASE
                    WHEN status = 'Pending'
                    THEN 1
                    ELSE 0
                END
            ) AS pending_invoices,

            SUM(
                CASE
                    WHEN status = 'Overdue'
                    THEN 1
                    ELSE 0
                END
            ) AS overdue_invoices

        FROM invoices
        WHERE user_id = %s
    """, (user_id,))

    stats = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "invoice.html",
        company=company,
        invoices=invoices,
        total_invoices=stats["total_invoices"] or 0,
        total_amount=stats["total_amount"] or 0,
        paid_amount=stats["paid_amount"] or 0,
        pending_amount=stats["pending_amount"] or 0,
        overdue_amount=stats["overdue_amount"] or 0,
        paid_invoices=stats["paid_invoices"] or 0,
        pending_invoices=stats["pending_invoices"] or 0,
        overdue_invoices=stats["overdue_invoices"] or 0,
        user_name=session.get("user_name"),
        user_email=session.get("user_email")
    )



# VIEW INVOICE


@app.route("/invoice/<int:invoice_id>")
def view_invoice(invoice_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM invoices
        WHERE id = %s
        AND user_id = %s
        LIMIT 1
    """, (invoice_id, user_id))

    invoice_data = cursor.fetchone()

    if invoice_data is None:
        cursor.close()
        db.close()

        flash("Invoice not found.", "error")
        return redirect(url_for("invoice"))

    cursor.execute("""
        SELECT *
        FROM companies
        WHERE user_id = %s
        LIMIT 1
    """, (user_id,))

    company = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "invoice_view.html",
        invoice=invoice_data,
        company=company,
        user_name=session.get("user_name"),
        user_email=session.get("user_email")
    )



# CREATE INVOICE


@app.route("/invoice/create", methods=["POST"])
def create_invoice():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    customer_name = request.form.get("customer_name", "").strip()
    customer_email = request.form.get("customer_email", "").strip()
    description = request.form.get("description", "").strip()
    amount = request.form.get("amount", "").strip()
    due_date = request.form.get("due_date", "").strip()
    notes = request.form.get("notes", "").strip()

    if not customer_name:
        flash("Customer name is required.", "error")
        return redirect(url_for("invoice"))

    if not amount:
        flash("Invoice amount is required.", "error")
        return redirect(url_for("invoice"))

    db = get_db_connection()
    cursor = db.cursor()

    # SAFE USER-SPECIFIC INVOICE NUMBER
    cursor.execute("""
        SELECT invoice_number
        FROM invoices
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,))

    latest = cursor.fetchone()

    if latest and latest[0]:
        try:
            number = int(
                latest[0].replace("INV-", "")
            ) + 1
        except ValueError:
            number = 1001
    else:
        number = 1001

    invoice_number = f"INV-{number}"

    cursor.execute("""
        INSERT INTO invoices
        (
            user_id,
            invoice_number,
            customer_name,
            customer_email,
            description,
            amount,
            due_date,
            status,
            notes
        )
        VALUES
        (
            %s,%s,%s,%s,%s,%s,%s,'Pending',%s
        )
    """, (
        user_id,
        invoice_number,
        customer_name,
        customer_email,
        description,
        amount,
        due_date if due_date else None,
        notes
    ))

    db.commit()

    cursor.close()
    db.close()

    flash("Invoice created successfully!", "success")

    return redirect(url_for("invoice"))



# MARK INVOICE AS PAID


@app.route("/invoice/<int:invoice_id>/paid", methods=["POST"])
def mark_invoice_paid(invoice_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE invoices
        SET status = 'Paid'
        WHERE id = %s
        AND user_id = %s
    """, (invoice_id, user_id))

    db.commit()

    cursor.close()
    db.close()

    flash("Invoice marked as paid.", "success")

    return redirect(url_for("invoice"))



# DELETE INVOICE


@app.route("/invoice/<int:invoice_id>/delete", methods=["POST"])
def delete_invoice(invoice_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        DELETE FROM invoices
        WHERE id = %s
        AND user_id = %s
    """, (invoice_id, user_id))

    db.commit()

    cursor.close()
    db.close()

    flash("Invoice deleted successfully.", "success")

    return redirect(url_for("invoice"))



# REMIND CUSTOMER


@app.route("/invoice/<int:invoice_id>/remind", methods=["POST"])
def remind_invoice(invoice_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT customer_name, customer_email, invoice_number
        FROM invoices
        WHERE id = %s
        AND user_id = %s
        LIMIT 1
    """, (invoice_id, user_id))

    invoice_data = cursor.fetchone()

    cursor.close()
    db.close()

    if not invoice_data:
        flash("Invoice not found.", "error")
        return redirect(url_for("invoice"))

    flash(
        f"Reminder prepared for {invoice_data['customer_name']}.",
        "success"
    )

    return redirect(url_for("invoice"))

@app.route("/items")
def items():

    # Make sure user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

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

      
        # INVENTORY ITEMS
      

        cursor.execute("""
            SELECT *
            FROM inventory
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))

        inventory = cursor.fetchall()

      
        # TOTAL ITEMS
      

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM inventory
            WHERE user_id = %s
        """, (user_id,))

        total_items = cursor.fetchone()["total"]

      
        # PRODUCTS
      

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM inventory
            WHERE user_id = %s
            AND item_type = 'Product'
        """, (user_id,))

        total_products = cursor.fetchone()["total"]

      
        # SERVICES
      

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM inventory
            WHERE user_id = %s
            AND item_type = 'Service'
        """, (user_id,))

        total_services = cursor.fetchone()["total"]

      
        # LOW STOCK
      

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM inventory
            WHERE user_id = %s
            AND item_type = 'Product'
            AND quantity > 0
            AND quantity <= low_stock_level
        """, (user_id,))

        low_stock = cursor.fetchone()["total"]

      
        # OUT OF STOCK
      

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM inventory
            WHERE user_id = %s
            AND item_type = 'Product'
            AND quantity <= 0
        """, (user_id,))

        out_of_stock = cursor.fetchone()["total"]

      
        # TOTAL INVENTORY VALUE
      

        cursor.execute("""
            SELECT COALESCE(
                SUM(quantity * cost_price),
                0
            ) AS total
            FROM inventory
            WHERE user_id = %s
            AND item_type = 'Product'
        """, (user_id,))

        inventory_value = cursor.fetchone()["total"]

        cursor.close()
        db.close()

        return render_template(
            "items.html",

            company=company,

            inventory=inventory,

            total_items=total_items,
            total_products=total_products,
            total_services=total_services,

            low_stock=low_stock,
            out_of_stock=out_of_stock,

            inventory_value=inventory_value,

            user_name=session["user_name"],
            user_email=session["user_email"]
        )

    except Exception as e:

        print("INVENTORY ERROR:", e)

        flash("Could not load inventory.", "error")

        return render_template(
            "items.html",
            company=company if "company" in locals() else None,
            inventory=[],
            total_items=0,
            total_products=0,
            total_services=0,
            low_stock=0,
            out_of_stock=0,
            inventory_value=0,
            user_name=session.get("user_name"),
            user_email=session.get("user_email")
        )
    
@app.route("/items/add", methods=["POST"])
def add_item():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    item_name = request.form.get("item_name", "").strip()
    sku = request.form.get("sku", "").strip()
    category = request.form.get("category", "").strip()

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

  
    # VALIDATION
  

    if not item_name:

        flash(
            "Item name is required.",
            "error"
        )

        return redirect(url_for("items"))

    try:

        quantity = float(quantity or 0)
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

        return redirect(url_for("items"))

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
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
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
        """, (
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
        ))

        db.commit()

        cursor.close()
        db.close()

        flash(
            f"{item_type} added successfully!",
            "success"
        )

    except Exception as e:

        print("ADD INVENTORY ERROR:", e)

        flash(
            "Could not add inventory item.",
            "error"
        )

    return redirect(url_for("items"))


@app.route("/items/edit/<int:item_id>", methods=["POST"])
def edit_item(item_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

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

        return redirect(url_for("items"))

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
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
        """, (
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
        ))

        db.commit()

        cursor.close()
        db.close()

        flash(
            "Inventory item updated successfully!",
            "success"
        )

    except Exception as e:

        print("EDIT INVENTORY ERROR:", e)

        flash(
            "Could not update inventory item.",
            "error"
        )

    return redirect(url_for("items"))

@app.route("/settings", methods=["GET", "POST"])
def settings():

    # Make sure user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

   
    # SAVE SETTINGS
   
    if request.method == "POST":

        # Company information
        company_name = request.form.get("company_name", "").strip()
        industry = request.form.get("industry", "").strip()
        specialization = request.form.get("specialization", "").strip()
        description = request.form.get("description", "").strip()

        # Contact information
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        website = request.form.get("website", "").strip()

        # Address
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        country = request.form.get("country", "").strip()

        # Services
        services = request.form.get("services", "").strip()

        
        # BANKING DETAILS
        
        bank_name = request.form.get("bank_name", "").strip()
        account_name = request.form.get("account_name", "").strip()
        account_number = request.form.get("account_number", "").strip()
        branch_code = request.form.get("branch_code", "").strip()
        payment_terms = request.form.get("payment_terms", "").strip()

        
        # LOGO UPLOAD
        
        logo = request.files.get("logo")
        logo_filename = None

        if logo and logo.filename:

            if not allowed_file(logo.filename):
                cursor.close()
                db.close()

                flash(
                    "Invalid logo format. Please use PNG, JPG or JPEG.",
                    "error"
                )

                return redirect(url_for("settings"))

            original_filename = secure_filename(logo.filename)

            extension = original_filename.rsplit(".", 1)[1].lower()

            logo_filename = f"company_{user_id}.{extension}"

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

        
        # CHECK IF COMPANY ALREADY EXISTS
        
        cursor.execute("""
            SELECT id, logo
            FROM companies
            WHERE user_id = %s
            LIMIT 1
        """, (user_id,))

        existing_company = cursor.fetchone()

        
        # UPDATE EXISTING COMPANY
        
        if existing_company:

            # If a new logo was uploaded
            if logo_filename:

                cursor.execute("""
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
                """, (
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
                ))

            # No new logo
            else:

                cursor.execute("""
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
                """, (
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
                ))

        
        # CREATE COMPANY IF IT DOESN'T EXIST
        
        else:

            cursor.execute("""
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
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s,

                    %s, %s, %s, %s, %s,

                    %s
                )
            """, (
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
            ))

        # Save changes
        db.commit()

        cursor.close()
        db.close()

        flash("Settings updated successfully!", "success")

        return redirect(url_for("settings"))

   
    # LOAD COMPANY SETTINGS
   

    cursor.execute("""
        SELECT *
        FROM companies
        WHERE user_id = %s
        LIMIT 1
    """, (user_id,))

    company = cursor.fetchone()

    cursor.close()
    db.close()

   
    # DEFAULT VALUES IF COMPANY DOES NOT EXIST
   

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

            # Banking
            "bank_name": "",
            "account_name": "",
            "account_number": "",
            "branch_code": "",
            "payment_terms": "",

            "logo": None
        }

   
    # OPEN SETTINGS PAGE
   

    return render_template(
        "settings.html",

        company=company,

        user_name=session.get("user_name"),
        user_email=session.get("user_email")
    )

# RUN APP

if __name__ == "__main__":
    app.run(debug=True)