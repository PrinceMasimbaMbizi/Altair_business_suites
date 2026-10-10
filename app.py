import types

from flask import (Flask,render_template,request,redirect,url_for,flash,session,send_from_directory,abort,jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date

import mysql.connector
import os


import requests


import cloudinary
import cloudinary.uploader

import json
import math
from datetime import datetime, date, timedelta

import pandas as pd
import numpy as np

from sklearn.linear_model import LinearRegression

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY") 

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)



# FLASK APP
app = Flask(__name__)


app.secret_key = os.environ.get("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY is not configured."
    )

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

def require_current_company():
    """
    Ensures that the authenticated user has a company.

    Returns:
        (user_id, company)
    """

    user_id = get_current_user_id()

    if not user_id:
        return None, None

    company = get_current_company()

    return user_id, company    


# CURRENT USER / COMPANY SECURITY
def get_current_user_id():
    """
    Returns the authenticated user's ID.

    IMPORTANT:
    Never take user_id from request.form, request.args,
    request.json, or the URL.
    Always use the Flask session.
    """

    return session.get("user_id")


def get_current_company():
    """
    Returns the company belonging to the currently
    authenticated user.

    The company is NEVER selected using a company_id
    supplied by the browser.
    """

    user_id = get_current_user_id()

    if not user_id:
        return None

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

        return cursor.fetchone()

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


def get_current_company_id():
    """
    Returns the database ID of the company belonging
    to the authenticated user.

    This value comes from the database after verifying
    ownership through the Flask session.
    """

    company = get_current_company()

    if not company:
        return None

    return company["id"]

# COMPANY LOGO

@app.route("/company-logo")
def company_logo():

    if "user_id" not in session:
        return "", 401

    user_id = session["user_id"]

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT logo
            FROM companies
            WHERE user_id = %s
            LIMIT 1
        """, (user_id,))

        company = cursor.fetchone()

        if not company or not company.get("logo"):
            return "", 404

        logo = company["logo"].strip()

        # Cloudinary or another externally hosted image
        if logo.startswith("https://") or logo.startswith("http://"):
            return redirect(logo)

        # Local image: accept only a filename, not a path
        if (
            "/" in logo
            or "\\" in logo
            or logo in (".", "..")
        ):
            return "", 404

        upload_folder = os.path.join(
            app.root_path,
            "static",
            "uploads"
        )

        logo_path = os.path.join(
            upload_folder,
            logo
        )

        if not os.path.isfile(logo_path):
            app.logger.warning(
                "Company logo file missing: %s",
                logo
            )
            return "", 404

        return send_from_directory(
            upload_folder,
            logo
        )

    except Exception:

        app.logger.exception(
            "COMPANY LOGO ROUTE ERROR"
        )

        return "", 500

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

    # Allow visitors to register even if they are not logged in.
    if request.method == "GET":

        return render_template(
            "register.html"
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    
    # VALIDATE INPUT

    if not name or not email or not password:

        flash(
            "Please fill in all fields.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if len(name) > 255:

        flash(
            "Your name is too long.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if len(email) > 254 or "@" not in email:

        flash(
            "Please enter a valid email address.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if len(password) < 8:

        flash(
            "Your password must contain at least 8 characters.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    
    # DATABASE CONNECTION
    

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        
        # CHECK WHETHER THE EMAIL ALREADY EXISTS
    
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s
            LIMIT 1
            """,
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            flash(
                "An account with this email already exists. "
                "Please log in instead.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        
        # HASH PASSWORD
        

        password_hash = generate_password_hash(
            password
        )

        
        # CREATE USER
        

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

        app.logger.info(
            "New user account created successfully."
        )

        flash(
            "Account created successfully. Please log in.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    except Exception as e:

        if db:

            try:
                db.rollback()

            except Exception:
                pass

        app.logger.exception(
            "REGISTER ERROR: %s",
            e
        )

        flash(
            "Could not create your account. "
            "Please try again.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    finally:

        if cursor:

            try:
                cursor.close()

            except Exception:
                pass

        if db:

            try:
                db.close()

            except Exception:
                pass





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


#company setup code
@app.route("/company-setup", methods=["GET", "POST"])
def company_setup():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "GET":
        return render_template("company_setup.html")

    print("========== COMPANY SETUP POST STARTED ==========")
    print("USER ID:", user_id)
    print("FORM FIELDS:", dict(request.form))
    print("UPLOADED FILES:", list(request.files.keys()))
    print("================================================")
    print("\n========== COMPANY SETUP DEBUG ==========")
    print("REQUEST METHOD:", request.method)
    print("USER ID:", session.get("user_id"))
    print("FORM DATA:", dict(request.form))
    print("FILES RECEIVED:", list(request.files.keys()))

    company_name = request.form.get("company_name", "").strip()
    industry = request.form.get("industry", "").strip()
    specialization = request.form.get("specialization", "").strip()
    description = request.form.get("description", "").strip()
    services = request.form.get("services", "").strip()

    print("\n========== COMPANY SETUP DEBUG ==========")
    print("USER ID:", session.get("user_id"))
    print("FORM DATA:", dict(request.form))
    print("FILES RECEIVED:", list(request.files.keys()))
    print("COMPANY NAME:", repr(company_name))
    print("INDUSTRY:", repr(industry))
    print("SPECIALIZATION:", repr(specialization))
    print("DESCRIPTION PROVIDED:", bool(description))
    print("SERVICES PROVIDED:", bool(services))
    print("========================================\n")
    
    # POST REQUEST
    # GET FORM DATA

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

    
    # VALIDATION
    

    if not company_name:
        print("COMPANY SETUP VALIDATION FAILED: company_name is empty")
        flash("Company name is required.", "error")
        return redirect(url_for("company_setup"))

    if not industry:
        print("COMPANY SETUP VALIDATION FAILED: industry is empty")
        flash("Please select your industry.", "error")
        return redirect(url_for("company_setup"))

    if not specialization:
        print("COMPANY SETUP VALIDATION FAILED: specialization is empty")
        flash("Please enter your company specialization.", "error")
        return redirect(url_for("company_setup"))

    if not description:

        print("COMPANY SETUP VALIDATION FAILED: description is empty")
        flash("Please enter your company description.", "error")
        return redirect(url_for("company_setup"))

    if not services:

        print("COMPANY SETUP VALIDATION FAILED: services is empty")
        flash("Please enter your company services or products.", "error")
        return redirect(url_for("company_setup"))

    
    # LOGO
    

    logo = request.files.get("logo")

    logo_url = None

    
    # UPLOAD LOGO ONLY IF USER SELECTED ONE
    

    if logo and logo.filename:

        
        # CHECK FILE TYPE
        

        if not allowed_file(logo.filename):

            flash(
                "Invalid logo format. Please use PNG, JPG or JPEG.",
                "error"
            )

            return redirect(
                url_for("company_setup")
            )

        
        # UPLOAD TO CLOUDINARY
        

        try:

            upload_result = cloudinary.uploader.upload(

                logo,

                folder="altair_business_suite/company_logos",

                public_id=f"company_{user_id}",

                overwrite=True,

                resource_type="image"
            )
            logo_url = upload_result.get("secure_url")

            
            # GET PERMANENT CLOUDINARY URL
            logo_url = upload_result.get(
                "secure_url"
            )

            print(
                "CLOUDINARY LOGO URL:",
                logo_url
            )

        except Exception as e:

            print(
                "CLOUDINARY LOGO UPLOAD ERROR:",
                e
            )

            flash(
                "Could not upload company logo.",
                "error"
            )

            return redirect(
                url_for("company_setup")
            )

    
    # DATABASE
    

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        
        # CHECK IF COMPANY ALREADY EXISTS
        

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

        
        # UPDATE EXISTING COMPANY
        

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

            
            # ONLY UPDATE LOGO IF A NEW LOGO WAS UPLOADED
            

            if logo_url:

                cursor.execute(
                    """
                    UPDATE companies
                    SET logo = %s
                    WHERE user_id = %s
                    """,
                    (
                        logo_url,
                        user_id
                    )
                )

        
        # CREATE NEW COMPANY
        

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
                    logo_url
                )
            )

        
        # COMMIT
        

        db.commit()

        flash(
            "Company profile created successfully!",
            "success"
        )

        return redirect(
            url_for("dashboard")
        )

    
    # DATABASE ERROR
    

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

    
    # CLOSE DATABASE
    

    finally:

        if cursor:

            cursor.close()

        if db:

            db.close()


# ALTAIR AI - REVENUE FORECASTING ENGINE
def predict_next_month_revenue(monthly_revenue):

    """
    Machine-learning revenue prediction.

    monthly_revenue:
        List of dictionaries:
        [
            {"month": "2026-04", "revenue": 50000},
            {"month": "2026-05", "revenue": 57000},
            ...
        ]

    Returns:
        prediction
        confidence
        model
    """

    if not monthly_revenue:
        return {
            "prediction": 0,
            "confidence": 0,
            "model": "Insufficient data"
        }

    cleaned = []

    for row in monthly_revenue:

        try:

            value = float(
                row.get("revenue", 0) or 0
            )

            cleaned.append(value)

        except Exception:
            cleaned.append(0)

    # Remove empty trailing periods
    while cleaned and cleaned[-1] == 0:
        cleaned.pop()

    # Not enough historical data
    if len(cleaned) < 3:

        if cleaned:

            prediction = sum(cleaned) / len(cleaned)

        else:

            prediction = 0

        return {
            "prediction": round(prediction, 2),
            "confidence": 25,
            "model": "Historical average"
        }

    # MACHINE LEARNING MODEL

    X = np.array(
        range(1, len(cleaned) + 1)
    ).reshape(-1, 1)

    y = np.array(cleaned)

    model = LinearRegression()

    model.fit(X, y)

    next_period = np.array(
        [[len(cleaned) + 1]]
    )

    prediction = model.predict(
        next_period
    )[0]

    # Revenue cannot be negative
    prediction = max(
        0,
        float(prediction)
    )

    
    # MODEL FIT

    try:

        r2 = model.score(X, y)

        confidence = int(
            max(
                20,
                min(
                    95,
                    r2 * 100
                )
            )
        )

    except Exception:

        confidence = 50

    return {
        "prediction": round(
            prediction,
            2
        ),
        "confidence": confidence,
        "model": "Linear Regression"
    }


# ALTAIR PERSONAL NLP ENGINE
ALTAIR_TRAINING_DATA = [

    
    # REVENUE
    

    (
        "How much revenue did I make?",
        "revenue"
    ),

    (
        "What is my revenue?",
        "revenue"
    ),

    (
        "How much money did my business make?",
        "revenue"
    ),

    (
        "Show me my sales revenue",
        "revenue"
    ),

    (
        "What are my sales?",
        "revenue"
    ),

    (
        "How much have I earned?",
        "revenue"
    ),

    (
        "How is my revenue doing?",
        "revenue"
    ),


    
    # FORECAST
    

    (
        "What will my revenue be next month?",
        "forecast"
    ),

    (
        "Predict my revenue",
        "forecast"
    ),

    (
        "How much will I make next month?",
        "forecast"
    ),

    (
        "What is my revenue forecast?",
        "forecast"
    ),

    (
        "Can you forecast my sales?",
        "forecast"
    ),

    (
        "What does the model predict?",
        "forecast"
    ),


    
    # EXPENSES
    

    (
        "How much are my expenses?",
        "expenses"
    ),

    (
        "Show me my expenses",
        "expenses"
    ),

    (
        "How much money am I spending?",
        "expenses"
    ),

    (
        "What are my business expenses?",
        "expenses"
    ),

    (
        "How much have I spent?",
        "expenses"
    ),


    
    # INVOICES
    

    (
        "How many invoices do I have?",
        "invoices"
    ),

    (
        "Show me my invoices",
        "invoices"
    ),

    (
        "How many invoices are pending?",
        "invoices"
    ),

    (
        "How many invoices are overdue?",
        "invoices"
    ),

    (
        "What invoices have been paid?",
        "invoices"
    ),


    
    # CUSTOMERS
    

    (
        "How many customers do I have?",
        "customers"
    ),

    (
        "Show me my customers",
        "customers"
    ),

    (
        "How many customers are there?",
        "customers"
    ),

    (
        "Tell me about my customers",
        "customers"
    ),


    
    # LEADS
    

    (
        "How many leads do I have?",
        "leads"
    ),

    (
        "Show me my leads",
        "leads"
    ),

    (
        "How are my leads performing?",
        "leads"
    ),

    (
        "What is my lead conversion rate?",
        "leads"
    ),

    (
        "How many leads converted?",
        "leads"
    ),


    
    # BUSINESS HEALTH
    

    (
        "How is my business doing?",
        "business_health"
    ),

    (
        "How healthy is my business?",
        "business_health"
    ),

    (
        "What is my business health score?",
        "business_health"
    ),

    (
        "Is my business performing well?",
        "business_health"
    ),

    (
        "Give me a business overview",
        "business_health"
    ),


    
    # RECOMMENDATIONS
    

    (
        "What should I do?",
        "recommendations"
    ),

    (
        "Give me business advice",
        "recommendations"
    ),

    (
        "What should I improve?",
        "recommendations"
    ),

    (
        "How can I improve my business?",
        "recommendations"
    ),

    (
        "What do you recommend?",
        "recommendations"
    ),


    
    # CASH FLOW
    

    (
        "How much money is outstanding?",
        "cash_flow"
    ),

    (
        "How much money am I waiting for?",
        "cash_flow"
    ),

    (
        "What is my cash flow situation?",
        "cash_flow"
    ),

    (
        "How much money is pending?",
        "cash_flow"
    ),

    (
        "How much money is overdue?",
        "cash_flow"
    )
]



# CREATE TRAINING ARRAYS


ALTAIR_QUESTIONS = [
    item[0]
    for item in ALTAIR_TRAINING_DATA
]

ALTAIR_INTENTS = [
    item[1]
    for item in ALTAIR_TRAINING_DATA
]



# ALTAIR NLP MODEL


altair_nlp_model = Pipeline(
    [
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                sublinear_tf=True
            )
        ),

        (
            "classifier",
            LogisticRegression(
                max_iter=1000
            )
        )
    ]
)



# TRAIN MODEL


altair_nlp_model.fit(
    ALTAIR_QUESTIONS,
    ALTAIR_INTENTS
)


print(
    "ALTAIR NLP MODEL TRAINED"
)

print(
    "Training examples:",
    len(ALTAIR_QUESTIONS)
)




# ALTAIR AI - IMPROVED QUESTION UNDERSTANDING


import re


def understand_altair_question(question):

    if not isinstance(question, str) or not question.strip():

        return {
            "intent": "unknown",
            "confidence": 0
        }

    
    # NORMALISE THE QUESTION
    

    question = question.lower().strip()

    question = re.sub(
        r"[^a-z0-9\s]",
        " ",
        question
    )

    question = re.sub(
        r"\s+",
        " ",
        question
    ).strip()

    
    # HELPER: MATCH BUSINESS PHRASES
    

    def contains_any(*phrases):

        return any(
            phrase in question
            for phrase in phrases
        )

    
    # 1. BUSINESS IMPROVEMENT AND RECOMMENDATIONS    

    if contains_any(
        "improve my business",
        "improve my cash flow",
        "improve cash flow",
        "increase my profits",
        "increase profits",
        "reduce my expenses",
        "reduce expenses",
        "reduce costs",
        "grow my business",
        "grow the business",
        "what should i focus on",
        "what should i do",
        "what should i improve",
        "what do you recommend",
        "give me business advice",
        "areas need attention",
        "areas of my business need attention",
        "which areas need attention",
        "areas to improve",
        "business priorities",
        "how can i improve",
        "how do i improve",
        "how can i increase sales",
        "how do i increase sales"
    ):

        return {
            "intent": "recommendations",
            "confidence": 99.0
        }

    
    # 2. OVERALL BUSINESS HEALTH
    

    if contains_any(
        "how is my business performing",
        "how is my business doing",
        "how is the business performing",
        "how is the business doing",
        "business performance",
        "business health",
        "how healthy is my business",
        "is my business performing well",
        "is my business doing well",
        "business overview",
        "overall business performance",
        "analyse my business",
        "analyze my business",
        "how well is my business doing",
        "how well is my business performing"
    ):

        return {
            "intent": "business_health",
            "confidence": 99.0
        }

    
    # 3. CASH FLOW
    

    if contains_any(
        "cash flow",
        "cashflow",
        "outstanding invoices",
        "money outstanding",
        "money am i waiting for",
        "unpaid invoices",
        "money owed to me",
        "amount owed to me",
        "pending payments",
        "overdue payments",
        "receivables",
        "how much money is pending",
        "how much money is overdue"
    ):

        return {
            "intent": "cash_flow",
            "confidence": 99.0
        }

    
    # 4. REVENUE
    

    if contains_any(
        "revenue",
        "sales revenue",
        "money did my business make",
        "how much have i earned",
        "how much did i earn",
        "how much have we earned",
        "income generated",
        "money made",
        "total sales",
        "sales performance"
    ):

        return {
            "intent": "revenue",
            "confidence": 99.0
        }

    
    # 5. EXPENSES
    

    if contains_any(
        "expenses",
        "business spending",
        "money am i spending",
        "money have i spent",
        "how much did i spend",
        "total spending",
        "operating costs",
        "business costs"
    ):

        return {
            "intent": "expenses",
            "confidence": 99.0
        }

    
    # 6. FORECASTING
    

    if contains_any(
        "forecast",
        "forecasting",
        "predict my revenue",
        "predict my sales",
        "next month revenue",
        "next month's revenue",
        "future revenue",
        "future sales",
        "revenue prediction",
        "sales prediction"
    ):

        return {
            "intent": "forecast",
            "confidence": 99.0
        }

    
    # 7. INVOICES
    

    if contains_any(
        "invoices",
        "invoice",
        "invoice status",
        "paid invoices",
        "pending invoices",
        "overdue invoices"
    ):

        return {
            "intent": "invoices",
            "confidence": 99.0
        }

    
    # 8. CUSTOMERS
    

    if contains_any(
        "customers",
        "customer",
        "client list",
        "how many clients",
        "my clients"
    ):

        return {
            "intent": "customers",
            "confidence": 99.0
        }

    
    # 9. LEADS
    

    if contains_any(
        "leads",
        "lead conversion",
        "potential customers",
        "prospects",
        "lead performance"
    ):

        return {
            "intent": "leads",
            "confidence": 99.0
        }

    
    # 10. EXISTING MACHINE-LEARNING MODEL
    
    # If no rule matches, let the existing NLP model decide.
    

    try:

        probabilities = (
            altair_nlp_model
            .predict_proba([question])[0]
        )

        classes = altair_nlp_model.classes_

        best_index = probabilities.argmax()

        intent = classes[best_index]

        confidence = float(
            probabilities[best_index] * 100
        )

        return {
            "intent": intent,
            "confidence": round(confidence, 2)
        }

    except Exception as e:

        print(
            "ALTAIR QUESTION UNDERSTANDING ERROR:",
            e
        )

        return {
            "intent": "unknown",
            "confidence": 0
        }

# ALTAIR AI 
def get_business_ai_data(user_id):

    db = None
    cursor = None

    try:

        
        # OPEN DATABASE CONNECTION
        

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        
        # SECURITY: RESOLVE COMPANY FROM AUTHENTICATED USER
        

        company = get_current_company()


        if not company:

            raise PermissionError(
                "No company is associated with the authenticated user."
            )

        # Extra ownership verification

        if int(company["user_id"]) != int(user_id):

            raise PermissionError(
                "Company ownership verification failed."
            )

        company_id = company["id"]

        
        # VERIFIED COMPANY INFORMATION
        

        verified_company = {

            "id": company_id,

            "company_name":
                company.get("company_name"),

            "industry":
                company.get("industry"),

            "specialization":
                company.get("specialization"),

            "description":
                company.get("description"),

            "services":
                company.get("services"),

            "city":
                company.get("city"),

            "country":
                company.get("country")
        }

        data = {}


        
        # COMPANY
        

        cursor.execute("""
            SELECT
                company_name,
                industry,
                specialization,
                description,
                services,
                city,
                country
            FROM companies
            WHERE user_id = %s
            LIMIT 1
        """, (user_id,))

        company = cursor.fetchone()

        data["company"] = company or {}

        
        # REVENUE BY MONTH
        

        cursor.execute("""
            SELECT
                DATE_FORMAT(
                    invoice_date,
                    '%Y-%m'
                ) AS month,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'Paid'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS revenue

            FROM invoices

            WHERE user_id = %s

            GROUP BY
                DATE_FORMAT(
                    invoice_date,
                    '%Y-%m'
                )

            ORDER BY month ASC

            LIMIT 24
        """, (user_id,))

        monthly_revenue = cursor.fetchall()

        data["monthly_revenue"] = (
            monthly_revenue or []
        )

        
        # INVOICE ANALYSIS
        

        cursor.execute("""
            SELECT

                COUNT(*) AS total,

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

                SUM(
                    CASE
                        WHEN status = 'Paid'
                        THEN 1
                        ELSE 0
                    END
                ) AS paid_count,

                SUM(
                    CASE
                        WHEN status = 'Pending'
                        THEN 1
                        ELSE 0
                    END
                ) AS pending_count,

                SUM(
                    CASE
                        WHEN status = 'Overdue'
                        THEN 1
                        ELSE 0
                    END
                ) AS overdue_count

            FROM invoices

            WHERE user_id = %s
        """, (user_id,))

        data["invoices"] = (
            cursor.fetchone() or {}
        )

        
        # CUSTOMERS
        

        cursor.execute("""
            SELECT
                COUNT(*) AS total
            FROM customers
            WHERE user_id = %s
        """, (user_id,))

        customer_data = cursor.fetchone()

        data["customers"] = (
            customer_data or {}
        )

        
        # LEADS
        

        cursor.execute("""
            SELECT

                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN lead_status = 'New'
                        THEN 1
                        ELSE 0
                    END
                ) AS new_leads,

                SUM(
                    CASE
                        WHEN lead_status = 'Contacted'
                        THEN 1
                        ELSE 0
                    END
                ) AS contacted,

                SUM(
                    CASE
                        WHEN lead_status = 'Interested'
                        THEN 1
                        ELSE 0
                    END
                ) AS interested,

                SUM(
                    CASE
                        WHEN lead_status = 'Converted'
                        THEN 1
                        ELSE 0
                    END
                ) AS converted

            FROM leads

            WHERE user_id = %s
        """, (user_id,))

        data["leads"] = (
            cursor.fetchone() or {}
        )

        
        # EXPENSES
        cursor.execute("""
            SELECT

                COUNT(*) AS count,

                COALESCE(
                    SUM(amount),
                    0
                ) AS total

            FROM expenses

            WHERE user_id = %s
        """, (user_id,))

        data["expenses"] = (
            cursor.fetchone() or {}
        )

   
        # INVESTMENTS

        cursor.execute("""
            SELECT

                COUNT(*) AS count,

                COALESCE(
                    SUM(amount),
                    0
                ) AS total

            FROM investments

            WHERE user_id = %s
        """, (user_id,))

        data["investments"] = (
            cursor.fetchone() or {}
        )


        # INVENTORY

        cursor.execute("""
            SELECT
                COUNT(*) AS total_items
            FROM items
            WHERE user_id = %s
        """, (user_id,))

        data["inventory"] = (
            cursor.fetchone() or {}
        )

        
        # RECURRING PAYMENTS

        cursor.execute("""
            SELECT

                COUNT(*) AS count,

                COALESCE(
                    SUM(
                        CASE
                            WHEN frequency = 'Monthly'
                            THEN amount

                            WHEN frequency = 'Weekly'
                            THEN amount * 4.33

                            WHEN frequency = 'Quarterly'
                            THEN amount / 3

                            WHEN frequency = 'Yearly'
                            THEN amount / 12

                            ELSE 0
                        END
                    ),
                    0
                ) AS monthly_cost

            FROM recurring_payments

            WHERE user_id = %s

            AND status = 'Active'
        """, (user_id,))

        data["recurring"] = (
            cursor.fetchone() or {}
        )

     
        # CALCULATED FORECAST

        forecast = predict_next_month_revenue(
            monthly_revenue
        )

        data["forecast"] = forecast

        return data

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()




# ALTAIR AI - BUSINESS ADVISOR


def generate_business_advice(business_data):

    invoices = business_data.get(
        "invoices",
        {}
    )

    leads = business_data.get(
        "leads",
        {}
    )

    expenses = business_data.get(
        "expenses",
        {}
    )

    recurring = business_data.get(
        "recurring",
        {}
    )

    forecast = business_data.get(
        "forecast",
        {}
    )

    paid_revenue = float(
        invoices.get(
            "paid_amount",
            0
        ) or 0
    )

    overdue_amount = float(
        invoices.get(
            "overdue_amount",
            0
        ) or 0
    )

    pending_amount = float(
        invoices.get(
            "pending_amount",
            0
        ) or 0
    )

    expense_total = float(
        expenses.get(
            "total",
            0
        ) or 0
    )

    monthly_recurring = float(
        recurring.get(
            "monthly_cost",
            0
        ) or 0
    )

    total_leads = int(
        leads.get(
            "total",
            0
        ) or 0
    )

    converted_leads = int(
        leads.get(
            "converted",
            0
        ) or 0
    )

    
    # CONVERSION RATE
    

    if total_leads > 0:

        conversion_rate = (
            converted_leads /
            total_leads
        ) * 100

    else:

        conversion_rate = 0

    
    # CASH PRESSURE
    

    cash_pressure = (
        overdue_amount +
        pending_amount
    )

    
    # BASIC BUSINESS HEALTH SCORE
    

    health_score = 70

    if overdue_amount > 0:
        health_score -= 10

    if conversion_rate < 10:
        health_score -= 10

    if monthly_recurring > paid_revenue:
        health_score -= 20

    if health_score < 0:
        health_score = 0

    if health_score > 100:
        health_score = 100

    return {
        "health_score": health_score,

        "paid_revenue": round(
            paid_revenue,
            2
        ),

        "overdue_amount": round(
            overdue_amount,
            2
        ),

        "pending_amount": round(
            pending_amount,
            2
        ),

        "expenses": round(
            expense_total,
            2
        ),

        "monthly_recurring": round(
            monthly_recurring,
            2
        ),

        "lead_conversion": round(
            conversion_rate,
            1
        ),

        "revenue_prediction": forecast.get(
            "prediction",
            0
        ),

        "prediction_confidence": forecast.get(
            "confidence",
            0
        )
    }    



# ALTAIR BUSINESS SUMMARY ENGINE


def altair_business_summary(
    business_data,
    analysis
):

    revenue = float(
        analysis.get(
            "paid_revenue",
            0
        ) or 0
    )

    forecast = float(
        analysis.get(
            "revenue_prediction",
            0
        ) or 0
    )

    confidence = float(
        analysis.get(
            "prediction_confidence",
            0
        ) or 0
    )

    overdue = float(
        analysis.get(
            "overdue_amount",
            0
        ) or 0
    )

    pending = float(
        analysis.get(
            "pending_amount",
            0
        ) or 0
    )

    expenses = float(
        analysis.get(
            "expenses",
            0
        ) or 0
    )

    conversion = float(
        analysis.get(
            "lead_conversion",
            0
        ) or 0
    )

    health = int(
        analysis.get(
            "health_score",
            0
        ) or 0
    )


    
    # HEALTH DESCRIPTION
    

    if health >= 80:

        health_text = (
            "The business currently shows "
            "strong overall indicators."
        )

    elif health >= 60:

        health_text = (
            "The business appears reasonably "
            "stable, but there are areas that "
            "should be monitored."
        )

    else:

        health_text = (
            "The business has several areas "
            "that require attention."
        )


    
    # BUILD RESPONSE
    

    return (
        "ALTAIR BUSINESS ANALYSIS\n\n"

        f"REVENUE:\n"
        f"Recorded paid revenue is "
        f"{revenue:,.2f}.\n\n"

        f"FORECAST:\n"
        f"The current machine-learning forecast "
        f"is {forecast:,.2f} with approximately "
        f"{confidence:.1f}% confidence. "
        f"This is a prediction and not a guarantee.\n\n"

        f"CASH FLOW:\n"
        f"Pending invoices total "
        f"{pending:,.2f}, while overdue invoices "
        f"total {overdue:,.2f}.\n\n"

        f"EXPENSES:\n"
        f"Recorded expenses total "
        f"{expenses:,.2f}.\n\n"

        f"SALES:\n"
        f"Lead conversion is currently "
        f"{conversion:.1f}%.\n\n"

        f"BUSINESS HEALTH:\n"
        f"Current Altair health score is "
        f"{health}/100. "
        f"{health_text}"
    )




# ALTAIR AI RESPONSE ENGINE
# Generates answers from the authenticated user's business data

def altair_response_engine(intent, business_data, analysis):

    
    # SAFELY READ BUSINESS DATA
    

    business_data = business_data or {}
    analysis = analysis or {}

    invoices = business_data.get("invoices") or {}
    customers = business_data.get("customers") or {}
    leads = business_data.get("leads") or {}
    expenses = business_data.get("expenses") or {}
    forecast = business_data.get("forecast") or {}
    recurring = business_data.get("recurring") or {}
    investments = business_data.get("investments") or {}
    inventory = business_data.get("inventory") or {}

    def number(data, key):
        try:
            return float(data.get(key, 0) or 0)
        except (TypeError, ValueError, AttributeError):
            return 0.0

    def count(data, key):
        return int(number(data, key))

    def money(value):
        return f"{value:,.2f}"

    
    # REVENUE
    

    if intent == "revenue":

        paid_revenue = number(invoices, "paid_amount")

        pending_amount = number(invoices, "pending_amount")

        overdue_amount = number(invoices, "overdue_amount")

        return (
            "Here is your recorded revenue overview:\n\n"
            f"Paid revenue: {money(paid_revenue)}\n"
            f"Pending invoices: {money(pending_amount)}\n"
            f"Overdue invoices: {money(overdue_amount)}\n\n"
            "Paid revenue represents money recorded against paid "
            "invoices. Pending and overdue invoices are amounts "
            "you may still need to collect."
        )

    
    # EXPENSES
    

    if intent == "expenses":

        total_expenses = number(expenses, "total")

        monthly_recurring = number(recurring, "monthly_cost")

        if total_expenses == 0:

            return (
                "Your current business data shows no recorded "
                "expenses in the expense total.\n\n"
                "If you have already recorded expenses, check that "
                "they are being saved correctly and associated "
                "with your account."
            )

        return (
            "Here is your expense overview:\n\n"
            f"Recorded expenses: {money(total_expenses)}\n"
            f"Estimated monthly recurring costs: "
            f"{money(monthly_recurring)}\n\n"
            "To control spending, review your largest expenses, "
            "compare recurring payments with your revenue, and "
            "identify costs that can be reduced without harming "
            "business operations."
        )

    
    # CASH FLOW
    

    if intent == "cash_flow":

        paid_revenue = number(invoices, "paid_amount")

        pending_amount = number(invoices, "pending_amount")

        overdue_amount = number(invoices, "overdue_amount")

        total_expenses = number(expenses, "total")

        monthly_recurring = number(recurring, "monthly_cost")

        outstanding = pending_amount + overdue_amount

        estimated_difference = paid_revenue - total_expenses

        return (
            "Here is your recorded cash-flow overview:\n\n"
            f"Paid invoice revenue: {money(paid_revenue)}\n"
            f"Pending invoices: {money(pending_amount)}\n"
            f"Overdue invoices: {money(overdue_amount)}\n"
            f"Total outstanding invoices: {money(outstanding)}\n"
            f"Recorded expenses: {money(total_expenses)}\n"
            f"Monthly recurring costs: {money(monthly_recurring)}\n\n"
            f"Paid revenue minus recorded expenses: "
            f"{money(estimated_difference)}\n\n"
            "Recommended actions:\n"
            "1. Follow up on overdue invoices.\n"
            "2. Contact customers with pending payments.\n"
            "3. Review recurring payments and unnecessary costs.\n"
            "4. Plan upcoming payments around expected collections.\n\n"
            "Important: The difference above is a simple comparison "
            "of the recorded totals. It is not necessarily your "
            "actual cash balance or accounting profit."
        )

    
    # INVOICES
    

    if intent == "invoices":

        total = count(invoices, "total")

        paid_count = count(invoices, "paid_count")

        pending_count = count(invoices, "pending_count")

        overdue_count = count(invoices, "overdue_count")

        pending_amount = number(invoices, "pending_amount")

        overdue_amount = number(invoices, "overdue_amount")

        return (
            "Here is your invoice overview:\n\n"
            f"Total invoices: {total}\n"
            f"Paid invoices: {paid_count}\n"
            f"Pending invoices: {pending_count}\n"
            f"Overdue invoices: {overdue_count}\n\n"
            f"Pending amount: {money(pending_amount)}\n"
            f"Overdue amount: {money(overdue_amount)}\n\n"
            "Recommended action: Prioritise overdue invoices, "
            "then follow up on pending payments."
        )

    
    # CUSTOMERS
    

    if intent == "customers":

        total_customers = count(customers, "total")

        return (
            "Here is your customer overview:\n\n"
            f"Total recorded customers: {total_customers}\n\n"
            "To improve customer retention, follow up with existing "
            "customers, respond quickly to enquiries, and identify "
            "customers who may need your services again.\n\n"
            "This summary uses your recorded customer count. "
            "Customer spending and retention trends require those "
            "additional figures to be available in your business data."
        )

    
    # LEADS
    

    if intent == "leads":

        total_leads = count(leads, "total")

        converted_leads = count(leads, "converted")

        if total_leads > 0:

            conversion_rate = (
                converted_leads / total_leads
            ) * 100

        else:

            conversion_rate = 0

        unconverted_leads = max(
            total_leads - converted_leads,
            0
        )

        return (
            "Here is your lead overview:\n\n"
            f"Total recorded leads: {total_leads}\n"
            f"Converted leads: {converted_leads}\n"
            f"Leads not recorded as converted: {unconverted_leads}\n"
            f"Recorded conversion rate: {conversion_rate:.1f}%\n\n"
            "Recommended actions:\n"
            "1. Follow up with promising leads.\n"
            "2. Contact leads who have not responded.\n"
            "3. Record lead outcomes accurately.\n"
            "4. Compare conversion rates over time.\n\n"
            "The conversion rate depends on the lead statuses "
            "recorded in your database."
        )

    
    # FORECASTING
    

    if intent == "forecast":

        prediction = number(forecast, "prediction")

        confidence = number(forecast, "confidence")

        if not forecast or "prediction" not in forecast:

            return (
                "I could not find a revenue forecast in your "
                "current business data.\n\n"
                "Check that your forecasting model has generated "
                "a prediction and that the result is included "
                "in get_business_ai_data()."
            )

        return (
            "Here is your revenue forecast:\n\n"
            f"Predicted revenue for the next month: "
            f"{money(prediction)}\n"
            f"Model confidence reported by your application: "
            f"{confidence:.1f}%\n\n"
            "This is a model-generated estimate, not a guarantee "
            "of future revenue. Its usefulness depends on the "
            "quality and quantity of your historical data."
        )

    
    # BUSINESS HEALTH
    

    if intent == "business_health":

        health_score = number(analysis, "health_score")

        paid_revenue = number(invoices, "paid_amount")

        total_expenses = number(expenses, "total")

        pending_amount = number(invoices, "pending_amount")

        overdue_amount = number(invoices, "overdue_amount")

        total_leads = count(leads, "total")

        converted_leads = count(leads, "converted")

        outstanding = pending_amount + overdue_amount

        if total_leads > 0:

            conversion_rate = (
                converted_leads / total_leads
            ) * 100

        else:

            conversion_rate = 0

        if health_score <= 0:

            health_description = (
                "A health score is not currently available."
            )

        elif health_score >= 80:

            health_description = (
                "Your recorded indicators suggest a strong position."
            )

        elif health_score >= 60:

            health_description = (
                "Your recorded indicators suggest room for improvement."
            )

        else:

            health_description = (
                "Your recorded indicators suggest that several "
                "areas may need attention."
            )

        return (
            "Here is your business performance overview:\n\n"
            f"Business health score: {health_score:.0f}/100\n"
            f"Paid invoice revenue: {money(paid_revenue)}\n"
            f"Recorded expenses: {money(total_expenses)}\n"
            f"Outstanding invoices: {money(outstanding)}\n"
            f"Recorded leads: {total_leads}\n"
            f"Converted leads: {converted_leads}\n"
            f"Lead conversion rate: {conversion_rate:.1f}%\n\n"
            f"{health_description}\n\n"
            "These figures describe the data currently available "
            "to Altair. The health score is an internal indicator, "
            "not a formal financial assessment."
        )

    
    # RECOMMENDATIONS
    

    if intent == "recommendations":

        recommendations = []

        pending_amount = number(invoices, "pending_amount")

        overdue_amount = number(invoices, "overdue_amount")

        paid_revenue = number(invoices, "paid_amount")

        total_expenses = number(expenses, "total")

        monthly_recurring = number(recurring, "monthly_cost")

        total_leads = count(leads, "total")

        converted_leads = count(leads, "converted")

        # Overdue invoices

        if overdue_amount > 0:

            recommendations.append(
                f"COLLECT OVERDUE PAYMENTS: You have "
                f"{money(overdue_amount)} in overdue invoices. "
                "Contact the affected customers and agree on "
                "payment dates."
            )

        # Pending invoices

        if pending_amount > 0:

            recommendations.append(
                f"FOLLOW UP ON PENDING INVOICES: "
                f"{money(pending_amount)} is pending. "
                "Send payment reminders and confirm expected "
                "payment dates."
            )

        # Expenses

        if total_expenses > 0:

            recommendations.append(
                f"REVIEW EXPENSES: Your recorded expense total is "
                f"{money(total_expenses)}. Review expense categories "
                "and identify avoidable costs."
            )

        # Recurring payments

        if monthly_recurring > 0:

            recommendations.append(
                f"CHECK RECURRING COSTS: Your estimated monthly "
                f"recurring payments are {money(monthly_recurring)}. "
                "Check whether each payment is still necessary."
            )

        # Leads

        if total_leads > converted_leads:

            recommendations.append(
                f"IMPROVE LEAD FOLLOW-UP: {total_leads - converted_leads} "
                "leads are not recorded as converted. Review them "
                "and follow up with promising prospects."
            )

        # Revenue compared with recorded expenses

        if total_expenses > paid_revenue:

            recommendations.append(
                "REVIEW REVENUE AND SPENDING: Recorded expenses "
                "exceed recorded paid invoice revenue. Review your "
                "financial records and upcoming payment obligations."
            )

        # No obvious issues

        if not recommendations:

            recommendations.append(
                "Keep your customer, invoice, lead, and expense "
                "records up to date. Review performance regularly "
                "so that changes are detected early."
            )

        return (
            "Here are Altair's recommendations based on your "
            "currently recorded business data:\n\n"
            + "\n\n".join(
                f"{index}. {item}"
                for index, item in enumerate(
                    recommendations,
                    start=1
                )
            )
        )

    
    # UNKNOWN OR UNSUPPORTED INTENT
    

    return (
        "I can analyse your recorded business information, "
        "but I could not confidently identify what you want to know.\n\n"
        "Try asking:\n"
        "• How is my business performing?\n"
        "• How much revenue have I collected?\n"
        "• How can I improve my cash flow?\n"
        "• Which invoices are overdue?\n"
        "• How can I reduce expenses?\n"
        "• How many leads have converted?\n"
        "• What should I improve in my business?\n"
        "• What is my revenue forecast?"
    )



# ALTAIR AI CHAT
@app.route(
    "/api/ai/chat",
    methods=["POST"]
)
def altair_ai_chat():

    
    # AUTHENTICATION
    

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message":
                "Please login first."

        }), 401


    user_id = session["user_id"]


    try:

        
        # GET USER MESSAGE
        

        body = (
            request
            .get_json(
                silent=True
            )
            or {}
        )


        message = (
            body
            .get(
                "message",
                ""
            )
            .strip()
        )


        if not message:

            return jsonify({

                "success": False,

                "message":
                    "Please enter a question."

            }), 400


        
        # GET AUTHENTICATED BUSINESS DATA
        

        business_data = (
            get_business_ai_data(
                user_id
            )
        )


        
        # CALCULATE BUSINESS ANALYTICS
        

        analysis = (
            generate_business_advice(
                business_data
            )
        )


        
        # OUR OWN NLP MODEL
        

        understanding = (
            understand_altair_question(
                message
            )
        )


        intent = understanding.get(
            "intent",
            "unknown"
        )


        confidence = float(
            understanding.get(
                "confidence",
                0
            )
        )


        
        # LOW CONFIDENCE
        

        if confidence < 35:

            return jsonify({

                "success": True,

                "reply":
                    "I am still learning how to "
                    "understand that type of question. "
                    "Try asking about revenue, "
                    "expenses, invoices, customers, "
                    "leads, cash flow, forecasting "
                    "or business health.",

                "intent": "unknown",

                "confidence": round(
                    confidence,
                    2
                )

            })


        
        # GENERATE ANSWER
        

        reply = (
            altair_response_engine(
                intent,
                business_data,
                analysis
            )
        )


        
        # RETURN RESPONSE
        

        return jsonify({

            "success": True,

            "reply": reply,

            "intent": intent,

            "confidence": round(
                confidence,
                2
            )

        })


    except Exception as e:

        print(
            "ALTAIR AI CHAT ERROR:",
            e
        )


        return jsonify({

            "success": False,

            "message":
                "Altair AI could not process "
                "your question."

        }), 500
















@app.route("/api/ai/business-insights", methods=["GET"])
def api_business_insights():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        
        # GET REAL BUSINESS DATA
        

        business_data = get_business_ai_data(user_id)

        analysis = generate_business_advice(
            business_data
        )

        ai_text = altair_business_summary(
            business_data,
            analysis
        )

        
        # REAL INVOICE STATISTICS
        

        invoice_data = (
            business_data.get("invoices", {})
            or {}
        )

        analysis["total_invoices"] = int(
            invoice_data.get("total", 0) or 0
        )

        analysis["paid_invoices"] = int(
            invoice_data.get("paid_count", 0) or 0
        )

        analysis["pending_invoices"] = int(
            invoice_data.get("pending_count", 0) or 0
        )

        analysis["overdue_invoices"] = int(
            invoice_data.get("overdue_count", 0) or 0
        )

        
        # CONNECT TO MYSQL
        

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        
        # MONTHLY REVENUE
        

        cursor.execute("""
            SELECT
                DATE_FORMAT(
                    invoice_date,
                    '%Y-%m'
                ) AS month,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'Paid'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS revenue

            FROM invoices

            WHERE user_id = %s

            AND invoice_date >= DATE_SUB(
                CURDATE(),
                INTERVAL 11 MONTH
            )

            GROUP BY DATE_FORMAT(
                invoice_date,
                '%Y-%m'
            )

            ORDER BY month ASC

        """, (user_id,))

        revenue_rows = (
            cursor.fetchall() or []
        )

        
        # MONTHLY EXPENSES
        

        cursor.execute("""
            SELECT
                DATE_FORMAT(
                    expense_date,
                    '%Y-%m'
                ) AS month,

                COALESCE(
                    SUM(amount),
                    0
                ) AS expenses

            FROM expenses

            WHERE user_id = %s

            AND expense_date >= DATE_SUB(
                CURDATE(),
                INTERVAL 11 MONTH
            )

            GROUP BY DATE_FORMAT(
                expense_date,
                '%Y-%m'
            )

            ORDER BY month ASC

        """, (user_id,))

        expense_rows = (
            cursor.fetchall() or []
        )

        
        # PREPARE MONTHLY DATA
        

        revenue_by_month = {
            str(row["month"]): float(
                row.get("revenue", 0) or 0
            )
            for row in revenue_rows
            if row.get("month")
        }

        expenses_by_month = {
            str(row["month"]): float(
                row.get("expenses", 0) or 0
            )
            for row in expense_rows
            if row.get("month")
        }

        
        # BUILD A CONTINUOUS 12-MONTH TIMELINE
        

        now = datetime.now()

        chart_labels = []
        revenue_history = []
        expense_history = []
        profit_history = []

        for offset in range(11, -1, -1):

            month_index = (
                now.year * 12
                + now.month
                - 1
            ) - offset

            year = month_index // 12

            month_number = (
                month_index % 12
            ) + 1

            month_key = (
                f"{year:04d}-{month_number:02d}"
            )

            month_date = datetime(
                year,
                month_number,
                1
            )

            revenue_value = round(
                revenue_by_month.get(
                    month_key,
                    0.0
                ),
                2
            )

            expense_value = round(
                expenses_by_month.get(
                    month_key,
                    0.0
                ),
                2
            )

            profit_value = round(
                revenue_value - expense_value,
                2
            )

            chart_labels.append(
                month_date.strftime("%b %Y")
            )

            revenue_history.append(
                revenue_value
            )

            expense_history.append(
                expense_value
            )

            profit_history.append(
                profit_value
            )

        
        # SEND GRAPH DATA TO DASHBOARD
        

        analysis["chart_labels"] = (
            chart_labels
        )

        analysis["revenue_history"] = (
            revenue_history
        )

        analysis["expense_history"] = (
            expense_history
        )

        analysis["profit_history"] = (
            profit_history
        )

        
        # RECENT INVOICES
        

        cursor.execute("""
            SELECT
                customer_name AS party,

                invoice_number AS reference,

                amount,

                status,

                invoice_date AS transaction_date

            FROM invoices

            WHERE user_id = %s

            ORDER BY
                invoice_date DESC,
                id DESC

            LIMIT 8

        """, (user_id,))

        invoice_transactions = (
            cursor.fetchall() or []
        )

        
        # RECENT EXPENSES
        

        cursor.execute("""
            SELECT
                expense_name AS party,

                category AS reference,

                amount,

                'Expense' AS status,

                expense_date AS transaction_date

            FROM expenses

            WHERE user_id = %s

            ORDER BY
                expense_date DESC,
                id DESC

            LIMIT 8

        """, (user_id,))

        expense_transactions = (
            cursor.fetchall() or []
        )

        
        # COMBINE TRANSACTIONS
        

        transactions = []

        for row in (
            invoice_transactions
            + expense_transactions
        ):

            transaction_date = row.get(
                "transaction_date"
            )

            transactions.append({

                "party": str(
                    row.get("party")
                    or "Business transaction"
                ),

                "reference": str(
                    row.get("reference")
                    or "—"
                ),

                "amount": round(
                    float(
                        row.get("amount", 0)
                        or 0
                    ),
                    2
                ),

                "status": str(
                    row.get("status")
                    or "Recorded"
                ),

                "transaction_date": (
                    transaction_date.isoformat()
                    if transaction_date
                    else ""
                )

            })

        # Newest transactions first.
        transactions.sort(
            key=lambda item: (
                item["transaction_date"]
            ),
            reverse=True
        )

        analysis["recent_transactions"] = (
            transactions[:8]
        )

        
        # RETURN DASHBOARD DATA
        

        return jsonify({

            "success": True,

            "analysis": analysis,

            "ai_advice": ai_text

        })

    except Exception as e:

        print(
            "ALTAIR BUSINESS INSIGHTS ERROR:",
            e
        )

        return jsonify({

            "success": False,

            "message": (
                "Otis could not load your "
                "business insights. Check "
                "the Flask console for the "
                "actual error."
            )

        }), 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


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



# CUSTOMER FINANCIAL HISTORY


@app.route("/customer/<int:customer_id>/history")
def customer_history(customer_id):

    # Ensure the user is logged in
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please log in first."
        }), 401

    user_id = session["user_id"]

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # ----------------------------------------------------
        # 1. Get customer belonging to the logged-in user
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                phone,
                company_name,
                total_spent
            FROM customers
            WHERE id = %s
              AND user_id = %s
            LIMIT 1
        """, (customer_id, user_id))

        customer_record = cursor.fetchone()

        if not customer_record:
            return jsonify({
                "success": False,
                "message": "Customer not found."
            }), 404

        # ----------------------------------------------------
        # 2. Get invoices linked to this customer
        # ----------------------------------------------------

        customer_email = (
            customer_record.get("email") or ""
        ).strip()

        customer_name = (
            customer_record.get("name") or ""
        ).strip()

        if customer_email:

            cursor.execute("""
                SELECT
                    id,
                    invoice_number,
                    customer_name,
                    customer_email,
                    item_name,
                    invoice_date,
                    due_date,
                    amount,
                    status
                FROM invoices
                WHERE user_id = %s
                  AND LOWER(TRIM(customer_email)) = LOWER(%s)
                ORDER BY invoice_date DESC, id DESC
            """, (
                user_id,
                customer_email
            ))

        else:

            cursor.execute("""
                SELECT
                    id,
                    invoice_number,
                    customer_name,
                    customer_email,
                    item_name,
                    invoice_date,
                    due_date,
                    amount,
                    status
                FROM invoices
                WHERE user_id = %s
                  AND LOWER(TRIM(customer_name)) = LOWER(%s)
                ORDER BY invoice_date DESC, id DESC
            """, (
                user_id,
                customer_name
            ))

        invoices = cursor.fetchall()

        # ----------------------------------------------------
        # 3. Calculate financial totals
        # ----------------------------------------------------

        total_invoiced = 0.0
        total_paid = 0.0
        outstanding_balance = 0.0
        overdue_balance = 0.0

        for invoice in invoices:

            amount = float(invoice.get("amount") or 0)

            status = (
                invoice.get("status") or ""
            ).strip().lower()

            total_invoiced += amount

            if status == "paid":

                total_paid += amount

            else:

                outstanding_balance += amount

                if status == "overdue":
                    overdue_balance += amount

            # Convert dates for JSON responses
            for date_field in ("invoice_date", "due_date"):

                date_value = invoice.get(date_field)

                if date_value is not None:
                    invoice[date_field] = str(date_value)

            # Ensure Decimal values can be serialized
            invoice["amount"] = amount

        # ----------------------------------------------------
        # 4. Return customer and invoice information
        # ----------------------------------------------------

        return jsonify({
            "success": True,

            "customer": {
                "id": customer_record["id"],
                "name": customer_record["name"],
                "email": customer_record.get("email"),
                "phone": customer_record.get("phone"),
                "company_name": customer_record.get("company_name")
            },

            "financial_summary": {
                "total_invoiced": round(total_invoiced, 2),
                "total_paid": round(total_paid, 2),
                "outstanding_balance": round(
                    outstanding_balance, 2
                ),
                "overdue_balance": round(overdue_balance, 2),
                "invoice_count": len(invoices)
            },

            "invoices": invoices
        })

    except Exception as e:

        app.logger.exception(
            "CUSTOMER FINANCIAL HISTORY ERROR"
        )

        return jsonify({
            "success": False,
            "message": "Could not load customer financial history."
        }), 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()






# EDIT CUSTOMER


@app.route(
    "/customer/<int:customer_id>/edit",
    methods=["POST"]
)
def edit_customer(customer_id):

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please log in first."
        }), 401

    user_id = session["user_id"]

    # Read submitted form data
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    company_name = request.form.get(
        "company_name", ""
    ).strip()

    address = request.form.get("address", "").strip()
    city = request.form.get("city", "").strip()
    country = request.form.get("country", "").strip()
    status = request.form.get("status", "Active").strip()
    notes = request.form.get("notes", "").strip()

    # Basic validation
    if not name:
        return jsonify({
            "success": False,
            "message": "Customer name is required."
        }), 400

    if status not in ("Active", "Inactive"):
        return jsonify({
            "success": False,
            "message": "Invalid customer status."
        }), 400

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            UPDATE customers
            SET
                name = %s,
                email = %s,
                phone = %s,
                company_name = %s,
                address = %s,
                city = %s,
                country = %s,
                status = %s,
                notes = %s
            WHERE id = %s
              AND user_id = %s
        """, (
            name,
            email,
            phone,
            company_name,
            address,
            city,
            country,
            status,
            notes,
            customer_id,
            user_id
        ))

        if cursor.rowcount == 0:

            # Check whether the customer exists and belongs
            # to this user, even if submitted values were unchanged.
            cursor.execute("""
                SELECT id
                FROM customers
                WHERE id = %s
                  AND user_id = %s
                LIMIT 1
            """, (customer_id, user_id))

            if not cursor.fetchone():
                db.rollback()

                return jsonify({
                    "success": False,
                    "message": "Customer not found."
                }), 404

        db.commit()

        return jsonify({
            "success": True,
            "message": "Customer updated successfully."
        })

    except Exception:

        if db:
            db.rollback()

        app.logger.exception("CUSTOMER UPDATE ERROR")

        return jsonify({
            "success": False,
            "message": "Could not update customer."
        }), 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()




# DELETE CUSTOMER


@app.route(
    "/customer/<int:customer_id>/delete",
    methods=["POST"]
)
def delete_customer(customer_id):

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please log in first."
        }), 401

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            DELETE FROM customers
            WHERE id = %s
              AND user_id = %s
        """, (
            customer_id,
            user_id
        ))

        if cursor.rowcount == 0:

            db.rollback()

            return jsonify({
                "success": False,
                "message": "Customer not found."
            }), 404

        db.commit()

        return jsonify({
            "success": True,
            "message": "Customer deleted successfully."
        })

    except Exception:

        if db:
            db.rollback()

        app.logger.exception("CUSTOMER DELETE ERROR")

        return jsonify({
            "success": False,
            "message": (
                "Could not delete customer. "
                "Check whether another table requires this customer record."
            )
        }), 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()                        


# INVOICE PAGE


@app.route("/invoice")
def invoice():

    
    # AUTHENTICATION
    

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(dictionary=True)

        
        # GET COMPANY DETAILS
        

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

        
        # GET USER'S INVOICES
        

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

        
        # INVOICE STATISTICS
        

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

        
        # RENDER INVOICE PAGE
        

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

    except Exception as e:

        print("INVOICE PAGE ERROR:", e)

        flash(
            "Could not load the invoice page. Please try again.",
            "error"
        )

        return redirect(url_for("dashboard"))

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()



# CREATE INVOICE


@app.route(
    "/invoice/create",
    methods=["POST"]
)
def create_invoice():

    
    # AUTHENTICATION
    

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    
    # GET FORM DATA
    

    customer_name = request.form.get(
        "customer_name",
        ""
    ).strip()

    customer_email = request.form.get(
        "customer_email",
        ""
    ).strip()

    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    # Support forms that use "description"
    # instead of "item_name".

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

    
    # VALIDATE CUSTOMER NAME
    

    if not customer_name:

        flash(
            "Customer name is required.",
            "error"
        )

        return redirect(url_for("invoice"))

    
    # VALIDATE ITEM DESCRIPTION
    

    if not item_name:

        flash(
            "Invoice item or description is required.",
            "error"
        )

        return redirect(url_for("invoice"))

    
    # VALIDATE AMOUNT
    

    try:

        amount_value = float(amount)

        if amount_value <= 0:
            raise ValueError

    except (ValueError, TypeError):

        flash(
            "Please enter a valid amount greater than zero.",
            "error"
        )

        return redirect(url_for("invoice"))

    
    # VALIDATE DUE DATE
    

    if due_date:

        try:

            due_date = date.fromisoformat(due_date)

        except ValueError:

            flash(
                "Please enter a valid invoice due date.",
                "error"
            )

            return redirect(url_for("invoice"))

    else:

        due_date = None

    
    # DATABASE VARIABLES
    

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        
        # GENERATE NEXT INVOICE NUMBER
              
        cursor.execute(
            """
            SELECT invoice_number
            FROM invoices
            WHERE user_id = %s
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

                if current_invoice.startswith("INV-"):

                    current_number = int(
                        current_invoice[4:]
                    )

                    if current_number > highest_number:

                        highest_number = current_number

            except (ValueError, TypeError):

                continue

        invoice_number = f"INV-{highest_number + 1}"

        
        # CURRENT INVOICE DATE
        

        invoice_date = date.today()

        
        # INSERT INVOICE
        

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
                due_date,
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
            "An invoice number conflict occurred. Please try again.",
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
            "Could not create the invoice. Please try again.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(url_for("invoice"))



# VIEW INDIVIDUAL INVOICE

@app.route(
    "/invoice/view/<int:invoice_id>",
    methods=["GET"]
)
def view_invoice(invoice_id):

    
    # AUTHENTICATION
    

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(dictionary=True)

        
        # GET COMPANY DETAILS
        

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

        
        # GET THE REQUESTED INVOICE
              

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

        
        # CHECK WHETHER INVOICE EXISTS
        

        if not invoice_data:

            return "Invoice not found.", 404

        
        # RENDER INDIVIDUAL INVOICE
        

        return render_template(
            "view_invoice.html",

            invoice=invoice_data,

            company=company,

            user_name=session.get("user_name"),

            user_email=session.get("user_email")
        )

    except Exception as e:

        print(
            "VIEW INVOICE ERROR:",
            e
        )

        return "Could not load the invoice.", 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()



# MARK INVOICE AS PAID


@app.route(
    "/invoice/<int:invoice_id>/paid",
    methods=["POST"]
)
def mark_invoice_paid(invoice_id):

    
    # AUTHENTICATION
    

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        
        # UPDATE ONLY THE LOGGED-IN USER'S INVOICE
        

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

        if cursor.rowcount > 0:

            flash(
                "Invoice marked as paid.",
                "success"
            )

        else:

            flash(
                "Invoice not found or already marked as paid.",
                "error"
            )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "MARK INVOICE PAID ERROR:",
            e
        )

        flash(
            "Could not update the invoice.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(url_for("invoice"))



# DELETE INVOICE
@app.route(
    "/invoice/<int:invoice_id>/delete",
    methods=["POST"]
)
def delete_invoice(invoice_id):

    
    # AUTHENTICATION
    

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        
        # DELETE ONLY THE LOGGED-IN USER'S INVOICE
        

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

        if cursor.rowcount > 0:

            flash(
                "Invoice deleted successfully.",
                "success"
            )

        else:

            flash(
                "Invoice not found.",
                "error"
            )

    except Exception as e:

        if db:
            db.rollback()

        print(
            "DELETE INVOICE ERROR:",
            e
        )

        flash(
            "Could not delete the invoice.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(url_for("invoice"))



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
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

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

        if cursor.rowcount > 0:

            flash(
                "Recurring payment stopped successfully.",
                "success"
            )

        else:

            flash(
                "Recurring payment was not found.",
                "error"
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

    return redirect(url_for("items"))



# RECURRING PAYMENT DATE CONVERTER


def convert_to_date(value):

    """
    Convert MySQL date values into Python date objects.

    Supports:
    - datetime.date
    - datetime.datetime
    - YYYY-MM-DD strings
    - YYYY-MM-DD HH:MM:SS strings
    """

    if value is None:
        return None

    if isinstance(value, datetime):

        return value.date()

    if isinstance(value, date):

        return value

    if isinstance(value, str):

        value = value.strip()

        if not value:
            return None

        try:

            # Handles YYYY-MM-DD and ISO datetime strings.
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).date()

        except ValueError:

            try:

                return date.fromisoformat(
                    value[:10]
                )

            except ValueError:

                raise ValueError(
                    f"Invalid recurring payment date: {value}"
                )

    raise TypeError(
        f"Unsupported date type: {type(value).__name__}"
    )



# PROCESS RECURRING PAYMENTS


def process_recurring_payments(
    conn,
    cursor,
    user_id
):

    today = date.today()

    try:

        
        # GET ACTIVE RECURRING PAYMENTS THAT ARE DUE
        

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

        
        # PROCESS EACH RECURRING PAYMENT
        

        for payment in recurring_payments:

            payment_id = payment["id"]

            payment_date = convert_to_date(
                payment["next_payment_date"]
            )

            end_date = convert_to_date(
                payment.get("end_date")
            )

            frequency = payment["frequency"]

            # Skip records without a valid next payment date.
            if payment_date is None:
                continue

            # ------------------------------------------------
            # PROCESS EVERY MISSED PAYMENT OCCURRENCE
            # ------------------------------------------------

            while payment_date <= today:

                # --------------------------------------------
                # CHECK END DATE
                # --------------------------------------------

                if (
                    end_date is not None
                    and payment_date > end_date
                ):

                    cursor.execute(
                        """
                        UPDATE recurring_payments
                        SET status = 'Completed'
                        WHERE id = %s
                        AND user_id = %s
                        """,
                        (
                            payment_id,
                            user_id
                        )
                    )

                    break

                # --------------------------------------------
                # CHECK FOR AN EXISTING PAYMENT RECORD
                # --------------------------------------------

                cursor.execute(
                    """
                    SELECT id
                    FROM recurring_payment_records
                    WHERE recurring_payment_id = %s
                    AND user_id = %s
                    AND payment_date = %s
                    LIMIT 1
                    """,
                    (
                        payment_id,
                        user_id,
                        payment_date
                    )
                )

                existing_record = cursor.fetchone()

                # --------------------------------------------
                # RECORD THE PAYMENT IF IT DOES NOT EXIST
                # --------------------------------------------

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

                    # ----------------------------------------
                    # CREATE THE ASSOCIATED EXPENSE
                    # ----------------------------------------

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

                # --------------------------------------------
                # CALCULATE THE NEXT PAYMENT DATE
                # --------------------------------------------

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

                else:

                    # Stop processing unsupported frequencies.
                    print(
                        f"Unsupported recurring payment frequency "
                        f"'{frequency}' for payment ID {payment_id}."
                    )

                    break

                next_date_result = cursor.fetchone()

                if not next_date_result:

                    raise RuntimeError(
                        f"Could not calculate the next payment date "
                        f"for recurring payment ID {payment_id}."
                    )

                next_payment_date = convert_to_date(
                    next_date_result["next_date"]
                )

                if next_payment_date is None:

                    raise RuntimeError(
                        f"Next payment date is missing for "
                        f"recurring payment ID {payment_id}."
                    )

                # Protect against an infinite loop.
                if next_payment_date <= payment_date:

                    raise RuntimeError(
                        f"Next payment date did not advance for "
                        f"recurring payment ID {payment_id}."
                    )

                payment_date = next_payment_date

            # ------------------------------------------------
            # SAVE THE NEXT PAYMENT DATE
            # ------------------------------------------------

            cursor.execute(
                """
                UPDATE recurring_payments
                SET next_payment_date = %s
                WHERE id = %s
                AND user_id = %s
                """,
                (
                    payment_date,
                    payment_id,
                    user_id
                )
            )

        
        # COMMIT SUCCESSFUL PROCESSING
        

        conn.commit()

    except Exception:

        conn.rollback()

        # Log the complete traceback in your application logs.
        import traceback

        print(
            "PROCESS RECURRING PAYMENTS ERROR:"
        )

        traceback.print_exc()

        # Propagate the error so the calling route can handle it.
        raise


























# INVENTORY + MONEY MANAGEMENT
@app.route("/items")
def items():

    
    # AUTHENTICATION
    

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        
        # DATABASE CONNECTION
        

        db = get_db_connection()

        if db is None:
            raise RuntimeError(
                "Database connection could not be established."
            )

        cursor = db.cursor(dictionary=True)

        
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
        

        # Recurring payment processing can fail if its database
        try:

            process_recurring_payments(
                db,
                cursor,
                user_id
            )

        except Exception as recurring_error:

            print(
                "\nRECURRING PAYMENT PROCESSING ERROR:",
                str(recurring_error)
            )

            import traceback
            traceback.print_exc()

            # Roll back any incomplete database transaction.
            try:
                db.rollback()
            except Exception:
                pass

            # Re-create the cursor after a rollback.
            try:
                cursor.close()
            except Exception:
                pass

            cursor = db.cursor(dictionary=True)

        
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
            SELECT
                COUNT(*) AS total,
                COALESCE(
                    SUM(
                        CASE
                            WHEN item_type = 'Product'
                            THEN 1 ELSE 0
                        END
                    ),
                    0
                ) AS total_products,
                COALESCE(
                    SUM(
                        CASE
                            WHEN item_type = 'Service'
                            THEN 1 ELSE 0
                        END
                    ),
                    0
                ) AS total_services,
                COALESCE(
                    SUM(
                        CASE
                            WHEN item_type = 'Product'
                             AND quantity > 0
                             AND quantity <= low_stock_level
                            THEN 1 ELSE 0
                        END
                    ),
                    0
                ) AS low_stock,
                COALESCE(
                    SUM(
                        CASE
                            WHEN item_type = 'Product'
                             AND quantity <= 0
                            THEN 1 ELSE 0
                        END
                    ),
                    0
                ) AS out_of_stock,
                COALESCE(
                    SUM(
                        CASE
                            WHEN item_type = 'Product'
                            THEN quantity * cost_price
                            ELSE 0
                        END
                    ),
                    0
                ) AS inventory_value
            FROM inventory
            WHERE user_id = %s
            """,
            (user_id,)
        )

        inventory_stats = cursor.fetchone() or {}

        total_items = inventory_stats.get("total", 0)
        total_products = inventory_stats.get("total_products", 0)
        total_services = inventory_stats.get("total_services", 0)
        low_stock = inventory_stats.get("low_stock", 0)
        out_of_stock = inventory_stats.get("out_of_stock", 0)
        inventory_value = inventory_stats.get("inventory_value", 0)

        
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
            SELECT
                COALESCE(SUM(amount), 0) AS total_expenses,
                COALESCE(
                    SUM(
                        CASE
                            WHEN MONTH(expense_date) = MONTH(CURRENT_DATE())
                             AND YEAR(expense_date) = YEAR(CURRENT_DATE())
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS month_expenses,
                COUNT(*) AS expense_count
            FROM expenses
            WHERE user_id = %s
            """,
            (user_id,)
        )

        expense_stats = cursor.fetchone() or {}

        total_expenses = expense_stats.get("total_expenses", 0)
        month_expenses = expense_stats.get("month_expenses", 0)
        expense_count = expense_stats.get("expense_count", 0)

        
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
            SELECT
                COALESCE(SUM(amount), 0) AS total_investments,
                COALESCE(SUM(expected_return), 0) AS expected_returns,
                COUNT(*) AS investment_count
            FROM investments
            WHERE user_id = %s
            """,
            (user_id,)
        )

        investment_stats = cursor.fetchone() or {}

        total_investments = investment_stats.get(
            "total_investments", 0
        )

        expected_returns = investment_stats.get(
            "expected_returns", 0
        )

        investment_count = investment_stats.get(
            "investment_count", 0
        )

        
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
            SELECT
                COUNT(
                    CASE
                        WHEN status = 'Active' THEN 1
                    END
                ) AS recurring_count,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status <> 'Active' THEN 0
                            WHEN frequency = 'Monthly' THEN amount
                            WHEN frequency = 'Weekly' THEN amount * 4.3333
                            WHEN frequency = 'Yearly' THEN amount / 12
                            ELSE 0
                        END
                    ),
                    0
                ) AS monthly_recurring

            FROM recurring_payments
            WHERE user_id = %s
            """,
            (user_id,)
        )

        recurring_stats = cursor.fetchone() or {}

        recurring_count = recurring_stats.get("recurring_count", 0)
        monthly_recurring = recurring_stats.get("monthly_recurring", 0)

        
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
            (user_id, user_id)
        )

        money_out_records = cursor.fetchall()

        
        # TOTAL MONEY OUT
        

        cursor.execute( """ SELECT (SELECT COALESCE(SUM(amount), 0)FROM expenses WHERE user_id = %s)+(SELECT COALESCE(SUM(amount), 0)FROM investments WHERE user_id = %s) AS total
            """,
            (user_id, user_id)
        )

        money_out_stats = cursor.fetchone() or {}
        total_money_out = money_out_stats.get("total", 0)

        
        # RENDER PAGE
        

        return render_template(
            "items.html",

            company=company,

            user_name=session.get("user_name"),
            user_email=session.get("user_email"),

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

            # Recurring payments
            recurring_payments=recurring_payments,
            recurring_count=recurring_count,
            monthly_recurring=monthly_recurring,

            # Money out
            money_out_records=money_out_records,
            total_money_out=total_money_out
        )

    except Exception as e:

        
        # LOG THE ACTUAL ERROR
        

        import traceback

        print("\n")
        print("=" * 70)
        print("ALTAIR BUSINESS SUITE - ITEMS PAGE ERROR")
        print("=" * 70)

        print("ERROR MESSAGE:", str(e))
        traceback.print_exc()

        print("=" * 70)
        print("\n")

        # Roll back only if a connection exists.
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass

        # Do not silently hide a missing database table or column.
        flash(f"INVENTORY ERROR: {str(e)}","error")

        return render_template(
            "items.html",

            company=None,
            user_name=session.get("user_name"),
            user_email=session.get("user_email"),

            # Inventory
            inventory=[],
            total_items=0,
            total_products=0,
            total_services=0,
            low_stock=0,
            out_of_stock=0,
            inventory_value=0,

            # Expenses
            expenses=[],
            total_expenses=0,
            month_expenses=0,
            expense_count=0,

            # Investments
            investments=[],
            total_investments=0,
            expected_returns=0,
            investment_count=0,

            # Recurring payments
            recurring_payments=[],
            recurring_count=0,
            monthly_recurring=0,

            # Money out
                money_out_records=[],
            total_money_out=0
        )

    finally:

        
        # CLOSE DATABASE RESOURCES SAFELY
        

        if cursor is not None:
            try:
                cursor.close()
            except Exception as close_error:
                print(
                    "ITEMS CURSOR CLOSE ERROR:",
                    close_error
                )

        if db is not None:
            try:
                db.close()
            except Exception as close_error:
                print(
                    "ITEMS DATABASE CLOSE ERROR:",
                    close_error
                )





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

            logo_url = None

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

                logo_url = (
                    f"company_{user_id}.{extension}"
                )

                os.makedirs(
                    app.config["UPLOAD_FOLDER"],
                    exist_ok=True
                )

                logo.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        logo_url
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

                if logo_url:

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
                            logo_url,
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

                        logo_url
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

        
        # GET CURRENT USER'S COMPANY
        

        cursor.execute("""
            SELECT *
            FROM companies
            WHERE user_id = %s
            LIMIT 1
        """, (user_id,))

        company = cursor.fetchone()

        
        # GET CURRENT USER'S LEADS
        

        cursor.execute("""
            SELECT *
            FROM leads
            WHERE user_id = %s
            ORDER BY id DESC
        """, (user_id,))

        leads = cursor.fetchall()

        
        # TOTAL LEADS
        

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM leads
            WHERE user_id = %s
        """, (user_id,))

        total_leads = cursor.fetchone()["total"]

        
        # NEW LEADS
        

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM leads
            WHERE user_id = %s
            AND lead_status = 'New'
        """, (user_id,))

        new_leads = cursor.fetchone()["total"]

        
        # CONTACTED LEADS
        

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM leads
            WHERE user_id = %s
            AND lead_status = 'Contacted'
        """, (user_id,))

        contacted_leads = cursor.fetchone()["total"]

        
        # INTERESTED LEADS
        

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM leads
            WHERE user_id = %s
            AND lead_status = 'Interested'
        """, (user_id,))

        interested_leads = cursor.fetchone()["total"]

        
        # CONVERTED LEADS
        

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM leads
            WHERE user_id = %s
            AND lead_status = 'Converted'
        """, (user_id,))

        converted_leads = cursor.fetchone()["total"]

        
        # OPEN AI LEAD FINDER
        

        return render_template(
            "ai_leads.html",
            company=company,
            leads=leads,
            total_leads=total_leads,
            new_leads=new_leads,
            contacted_leads=contacted_leads,
            interested_leads=interested_leads,
            converted_leads=converted_leads,
            user_name=session.get("user_name", ""),
            user_email=session.get("user_email", "")
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
            

# ADD AI LEAD MANUALLY

@app.route(
    "/ai-leads/add",
    methods=["POST"]
)
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


    
    # VALIDATION
    

    if not company_name:

        flash(
            "Company name is required.",
            "error"
        )

        return redirect(
            url_for("ai_leads")
        )


    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()


        
        # INSERT LEAD
        

        cursor.execute(
            """
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
                ai_analysis,
                ai_reason,
                ai_message,
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
                'New',
                0,
                '',
                '',
                '',
                %s
            )
            """,
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
                notes
            )
        )


        db.commit()


        flash(
            "Lead added successfully!",
            "success"
        )


    except Exception as e:

        if db:
            db.rollback()

        print(
            "ADD AI LEAD ERROR:",
            e
        )

        flash(
            "Could not add lead.",
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




@app.route(
    "/ai-leads/<int:lead_id>/status",
    methods=["POST"]
)
def update_lead_status(lead_id):

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




# AI LEAD FINDER - GOOGLE PLACES SEARCH


@app.route(
    "/ai-leads/search",
    methods=["POST"]
)
def search_ai_leads():

    
    # CHECK LOGIN
    

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]


    
    # GET SEARCH INPUTS
    

    services = request.form.get(
        "services",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    industry = request.form.get(
        "industry",
        ""
    ).strip()

    business_size = request.form.get(
        "business_size",
        ""
    ).strip()

    keywords = request.form.get(
        "keywords",
        ""
    ).strip()


    
    # MAX RESULTS
    

    try:

        max_results = int(
            request.form.get(
                "max_results",
                10
            )
        )

    except (
        ValueError,
        TypeError
    ):

        max_results = 10


    # Keep Google request reasonable

    max_results = max(
        1,
        min(
            max_results,
            20
        )
    )


    
    # VALIDATION
    

    if not services:

        flash(
            "Please enter the service or product you offer.",
            "error"
        )

        return redirect(
            url_for("ai_leads")
        )


    if not location:

        flash(
            "Please enter the target location.",
            "error"
        )

        return redirect(
            url_for("ai_leads")
        )


    if not GOOGLE_PLACES_API_KEY:

        flash(
            "Google Places API key is not configured.",
            "error"
        )

        return redirect(
            url_for("ai_leads")
        )


    
    # BUILD CUSTOMER DISCOVERY QUERY
    
    #
    # IMPORTANT:
    #
    # "services" is what OUR company sells.
    #
    # We do NOT put the service directly into the
    # Google Places search because that can cause
    # Google to find our competitors.
    #
    # Example:
    #
    # Service we sell:
    # Website Development
    #
    # Target industry:
    # Restaurants
    #
    # Location:
    # Cape Town
    #
    # Google search:
    #
    # Restaurants in Cape Town
    #
    # The service is used later to qualify the lead.
    

    query_parts = []


    
    # TARGET INDUSTRY
    

    if industry:

        query_parts.append(
            industry
        )

    else:

        query_parts.append(
            "businesses"
        )


    
    # BUSINESS SIZE
    

    if (
        business_size
        and
        business_size.lower() != "any"
    ):

        query_parts.append(
            business_size
            + " businesses"
        )


    
    # EXTRA KEYWORDS
    

    if keywords:

        query_parts.append(
            keywords
        )


    
    # LOCATION
    

    query_parts.append(
        "in " + location
    )


    
    # FINAL GOOGLE QUERY
    

    search_query = " ".join(
        query_parts
    )


    
    # DEBUG INFORMATION
    

    print("=" * 70)

    print(
        "AI LEAD SEARCH"
    )

    print("=" * 70)

    print(
        "Service / Product:",
        services
    )

    print(
        "Target Location:",
        location
    )

    print(
        "Target Industry:",
        industry
    )

    print(
        "Business Size:",
        business_size
    )

    print(
        "Keywords:",
        keywords
    )

    print(
        "Google Customer Query:",
        search_query
    )

    print("=" * 70)


    
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
            max_results
    }


    
    # SEND GOOGLE REQUEST
    

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
                "Please check your Google Places API configuration.",
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


    
    # PROCESS GOOGLE RESULTS
    

    google_results = []


    for place in data.get(
        "places",
        []
    ):


        
        # COMPANY NAME
        

        display_name = place.get(
            "displayName",
            {}
        )


        company_name = display_name.get(
            "text",
            "Unknown Business"
        )


        
        # PHONE
        

        phone = (

            place.get(
                "nationalPhoneNumber"
            )

            or

            place.get(
                "internationalPhoneNumber"
            )

            or

            ""
        )


        
        # GOOGLE BUSINESS TYPES
        

        types = place.get(
            "types",
            []
        )


        
        # DETERMINE INDUSTRY
        

        industry_name = ""


        ignored_types = {

            "point_of_interest",

            "establishment",

            "store",

            "premise",

            "political",

            "locality",

            "geocode"
        }


        for place_type in types:

            if place_type not in ignored_types:

                industry_name = (

                    place_type

                    .replace(
                        "_",
                        " "
                    )

                    .title()
                )

                break


        
        # FALLBACK INDUSTRY
        

        if not industry_name:

            industry_name = industry


        
        # ADDRESS
        

        address = place.get(
            "formattedAddress",
            ""
        )


        
        # WEBSITE
        

        website = place.get(
            "websiteUri",
            ""
        )


        
        # BUSINESS STATUS
        

        business_status = place.get(
            "businessStatus",
            ""
        )


        
        # GOOGLE MAPS URL
        

        google_maps_url = place.get(
            "googleMapsUri",
            ""
        )


        
        # BUILD POTENTIAL LEAD
        

        potential_lead = {

            "google_place_id":
                place.get(
                    "id",
                    ""
                ),

            "company_name":
                company_name,

            "address":
                address,

            "website":
                website,

            "phone":
                phone,

            "industry":
                industry_name,

            "types":
                types,

            "business_status":
                business_status,

            "google_maps_url":
                google_maps_url
        }


        
        # CHECK FOR COMPETITOR
        

        if is_likely_competitor(

            potential_lead,

            services
        ):

            print(
                "COMPETITOR SKIPPED:",
                company_name
            )

            continue


        
        # QUALIFY THE LEAD
        

        qualification = qualify_lead_with_ai(

            lead=potential_lead,

            service=services,

            target_industry=industry,

            target_location=location,

            business_size=business_size,

            keywords=keywords
        )


        
        # ADD AI QUALIFICATION
        

        potential_lead.update({

            "lead_score":
                qualification.get(
                    "lead_score",
                    0
                ),

            "ai_analysis":
                qualification.get(
                    "ai_analysis",
                    ""
                ),

            "ai_reason":
                qualification.get(
                    "ai_reason",
                    ""
                ),

            "ai_message":
                qualification.get(
                    "ai_message",
                    ""
                ),

            "lead_quality":
                qualification.get(
                    "lead_quality",
                    "Potential Lead"
                )
        })


        
        # ADD RESULT
        

        google_results.append(
            potential_lead
        )


    
    # SORT RESULTS BY LEAD SCORE
    

    google_results.sort(

        key=lambda lead:
            lead.get(
                "lead_score",
                0
            ),

        reverse=True
    )


    
    # NO RESULTS
    

    if not google_results:

        flash(
            "No suitable potential customers were found. "
            "Try changing the location, industry or keywords.",
            "error"
        )


    
    # LOAD AI LEAD FINDER PAGE
    

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

        search_services=services,

        search_location=location,

        search_industry=industry,

        search_business_size=business_size,

        search_keywords=keywords,

        user_name=session.get(
            "user_name"
        ),

        user_email=session.get(
            "user_email"
        )
    )



# GET COMPANY FOR CURRENT USER


def get_company_for_user(
    user_id
):

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
        (
            user_id,
        )
    )

    company = cursor.fetchone()

    cursor.close()

    db.close()

    return company



# GET LEADS FOR CURRENT USER


def get_leads_for_user(
    user_id
):

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT *
        FROM leads
        WHERE user_id = %s
        ORDER BY id DESC
        """,
        (
            user_id,
        )
    )

    leads = cursor.fetchall()

    cursor.close()

    db.close()

    return leads



# GET TOTAL LEADS


def get_lead_count(
    user_id
):

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM leads
        WHERE user_id = %s
        """,
        (
            user_id,
        )
    )

    result = cursor.fetchone()

    cursor.close()

    db.close()

    return result["total"]



# GET LEADS BY STATUS


def get_lead_status_count(
    user_id,
    status
):

    db = get_db_connection()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM leads
        WHERE user_id = %s
        AND lead_status = %s
        """,
        (
            user_id,
            status
        )
    )

    result = cursor.fetchone()

    cursor.close()

    db.close()

    return result["total"]



# CHECK IF BUSINESS IS LIKELY A COMPETITOR


def is_likely_competitor(
    lead,
    service
):

    company_name = lead.get(
        "company_name",
        ""
    ).lower()


    industry = lead.get(
        "industry",
        ""
    ).lower()


    website = lead.get(
        "website",
        ""
    ).lower()


    
    # COMPETITOR TERMS
    

    competitor_terms = [

        "web design",

        "web development",

        "website design",

        "website development",

        "web developer",

        "website developer",

        "digital agency",

        "digital marketing agency",

        "software development",

        "software company",

        "app development",

        "application development",

        "web agency",

        "website agency",

        "seo agency",

        "marketing agency"
    ]


    
    # COMBINE BUSINESS INFORMATION
    

    combined_text = (

        company_name

        + " "

        + industry

        + " "

        + website
    )


    
    # CHECK TERMS
    

    for term in competitor_terms:

        if term in combined_text:

            return True


    return False






def qualify_lead_with_ai(

    lead,

    service,

    target_industry,

    target_location,

    business_size,

    keywords

):

    score = 0

    reasons = []

    analysis_points = []


    
    # LEAD INFORMATION
    

    company_name = lead.get(
        "company_name",
        ""
    )

    website = lead.get(
        "website",
        ""
    )

    industry = lead.get(
        "industry",
        ""
    )

    location = lead.get(
        "address",
        ""
    )

    business_status = lead.get(
        "business_status",
        ""
    )


    
    # BUSINESS STATUS
    

    if business_status == "OPERATIONAL":

        score += 10

        analysis_points.append(
            "The business is currently listed as operational."
        )


    
    # INDUSTRY MATCH
    

    if target_industry:

        industry_lower = industry.lower()

        target_lower = target_industry.lower()


        if (

            target_lower in industry_lower

            or

            industry_lower in target_lower
        ):

            score += 25

            reasons.append(
                "The business matches the target industry."
            )

            analysis_points.append(

                "The business appears to match "
                "the requested target industry: "
                + target_industry
                + "."
            )

        else:

            analysis_points.append(

                "The business may not exactly match "
                "the requested target industry."
            )


    
    # WEBSITE CHECK
    

    if not website:

        score += 35

        reasons.append(
            "No website was found in the Google business listing."
        )

        analysis_points.append(

            "No website was found for this business. "
            "This may represent a strong opportunity "
            "for "
            + service
            + "."
        )

    else:

        score += 5

        analysis_points.append(

            "The business already has a website listed."
        )


    
    # LOCATION MATCH
    

    if target_location:

        if target_location.lower() in location.lower():

            score += 15

            analysis_points.append(

                "The business appears to be located "
                "in the requested target area."
            )


    
    # SERVICE BEING SOLD
    

    if service:

        analysis_points.append(

            "The requested service or product being "
            "sold is: "
            + service
            + "."
        )


    
    # BUSINESS SIZE
    

    if (

        business_size

        and

        business_size.lower() != "any"
    ):

        analysis_points.append(

            "The requested business size is: "
            + business_size
            + "."
        )


    
    # KEYWORDS
    

    if keywords:

        analysis_points.append(

            "Additional search requirements: "
            + keywords
            + "."
        )


    
    # LIMIT SCORE
    

    score = max(
        0,
        min(
            score,
            100
        )
    )


    
    # LEAD QUALITY
    

    if score >= 80:

        quality = (
            "Excellent potential lead"
        )

    elif score >= 60:

        quality = (
            "Strong potential lead"
        )

    elif score >= 40:

        quality = (
            "Potential lead"
        )

    elif score >= 20:

        quality = (
            "Weak potential lead"
        )

    else:

        quality = (
            "Low potential lead"
        )


    
    # AI ANALYSIS
    

    ai_analysis = (

        company_name

        + " was identified as a potential customer "
          "for "

        + service

        + ". "

        + " ".join(
            analysis_points
        )
    )


    
    # AI REASON
    

    if reasons:

        ai_reason = " ".join(
            reasons
        )

    else:

        ai_reason = (

            quality

            + ". Additional research is recommended "
              "before contacting the business."
        )


    
    # OUTREACH MESSAGE
    

    ai_message = (

        "Hi "

        + company_name

        + ",\n\n"

        + "I came across your business while researching "
          "companies in "

        + target_location

        + ".\n\n"

        + "We provide "

        + service

        + " and help businesses improve their "
          "operations, online presence and customer "
          "experience.\n\n"

        + "I would be happy to discuss how we could "
          "potentially help your business.\n\n"

        + "Kind regards,\n"

        + "Skies Altair Technologies"
    )


    
    # RETURN QUALIFICATION
    

    return {

        "lead_score":
            score,

        "ai_analysis":
            ai_analysis,

        "ai_reason":
            ai_reason,

        "ai_message":
            ai_message,

        "lead_quality":
            quality
    }



#saving the google leads
@app.route("/save-google-lead", methods=["POST"])
def save_google_lead():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    user_id = session["user_id"]

    company_name = request.form.get("company_name", "").strip()
    industry = request.form.get("industry", "").strip()
    location = request.form.get("location", "").strip()
    website = request.form.get("website", "").strip()
    phone = request.form.get("phone", "").strip()
    google_place_id = request.form.get("google_place_id", "").strip()

    if not company_name:
        return jsonify({
            "success": False,
            "message": "Company name is required."
        }), 400

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        
        # CHECK IF THIS GOOGLE LEAD IS ALREADY SAVED
        

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

            cursor.close()
            db.close()

            return jsonify({
                "success": True,
                "already_saved": True,
                "lead_id": existing["id"],
                "message": "Lead already saved."
            })


        
        # SAVE NEW LEAD
        

        cursor.execute("""
            INSERT INTO leads
            (
                user_id,
                company_name,
                industry,
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
                %s,
                'Google',
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
            phone,
            google_place_id
        ))

        lead_id = cursor.lastrowid

        db.commit()

        cursor.close()
        db.close()


        
        # RETURN JSON
        

        return jsonify({
            "success": True,
            "already_saved": False,
            "lead_id": lead_id,
            "message": "Lead saved successfully!",
            "lead": {
                "id": lead_id,
                "company_name": company_name,
                "industry": industry,
                "location": location,
                "phone": phone,
                "website": website,
                "lead_status": "New",
                "lead_score": 0
            }
        })


    except Exception as e:

        print("SAVE GOOGLE LEAD ERROR:", e)

        return jsonify({
            "success": False,
            "message": "Could not save lead."
        }), 500
    

# RUN APP
if __name__ == "__main__":

    app.run(
        debug=True
    )