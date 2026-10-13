import types

from flask import (Flask,render_template,request,redirect,url_for,flash as _flask_flash,session,send_from_directory,abort,jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date

import mysql.connector
import os
import re


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


# ================================================================
# ALTAIR UI: INLINE TOAST NOTIFICATIONS + LOADING INDICATOR
# All UI assets are embedded here so no additional static files are needed.
# ================================================================
ALTAIR_UI_CSS = r"""#altair-toast-container{position:fixed;top:22px;right:22px;z-index:2147483000;display:flex;flex-direction:column;gap:11px;width:min(390px,calc(100vw - 28px));pointer-events:none}
.altair-toast{pointer-events:auto;display:flex;align-items:flex-start;gap:12px;padding:15px 16px;border:1px solid rgba(255,255,255,.13);border-radius:16px;background:rgba(17,17,28,.96);color:#f7f8ff;box-shadow:0 18px 55px rgba(0,0,0,.28);backdrop-filter:blur(18px);font:500 14px/1.45 Inter,system-ui,sans-serif;animation:altairToastIn .28s ease both;overflow:hidden}
.altair-toast::before{content:"";width:4px;align-self:stretch;flex:0 0 4px;border-radius:5px;background:#00f0ff}.altair-toast.success::before{background:#22c55e}.altair-toast.error::before{background:#fb7185}.altair-toast.warning::before{background:#fbbf24}.altair-toast .altair-toast-icon{font-size:19px;line-height:1.2}.altair-toast .altair-toast-message{flex:1;overflow-wrap:anywhere}.altair-toast .altair-toast-close{border:0;background:transparent;color:#aab0c7;cursor:pointer;font-size:20px;line-height:1;padding:0 0 0 4px}.altair-toast.hide{animation:altairToastOut .22s ease forwards}
@keyframes altairToastIn{from{opacity:0;transform:translateX(18px)}to{opacity:1;transform:translateX(0)}}@keyframes altairToastOut{to{opacity:0;transform:translateX(18px)}}
#altair-loading-overlay{position:fixed;inset:0;z-index:2147482000;display:none;align-items:center;justify-content:center;padding:24px;background:rgba(6,8,20,.72);backdrop-filter:blur(9px)}#altair-loading-overlay.show{display:flex}
.altair-loading-card{width:min(440px,100%);padding:30px 28px;border:1px solid rgba(0,240,255,.28);border-radius:24px;background:linear-gradient(145deg,rgba(20,23,43,.98),rgba(13,14,27,.98));color:#f8faff;text-align:center;box-shadow:0 22px 80px rgba(0,0,0,.4),0 0 40px rgba(0,240,255,.08);font-family:Inter,system-ui,sans-serif}
.altair-loader-orbit{width:66px;height:66px;margin:0 auto 20px;border-radius:50%;border:3px solid rgba(0,240,255,.13);border-top-color:#00f0ff;border-right-color:#ff00d4;animation:altairSpin .9s linear infinite;position:relative}.altair-loader-orbit::after{content:"";position:absolute;inset:10px;border:2px dashed rgba(255,0,212,.65);border-radius:50%;animation:altairSpin 4s linear infinite reverse}@keyframes altairSpin{to{transform:rotate(360deg)}}
.altair-loading-title{font-size:20px;font-weight:800;margin:0 0 8px}.altair-loading-message{font-size:14px;color:#b8c1da;min-height:22px;margin:0}.altair-loading-track{height:5px;border-radius:99px;background:rgba(255,255,255,.09);overflow:hidden;margin:22px 0 0}.altair-loading-track span{display:block;height:100%;width:38%;border-radius:99px;background:linear-gradient(90deg,#00f0ff,#9d4edd,#ff00d4);animation:altairProgress 1.5s ease-in-out infinite alternate}@keyframes altairProgress{from{transform:translateX(-20%);width:25%}to{transform:translateX(280%);width:48%}}
button.altair-submitting{opacity:.72;cursor:wait!important}
@media(max-width:520px){#altair-toast-container{top:12px;right:12px;width:calc(100vw - 24px)}.altair-toast{padding:13px;border-radius:13px}.altair-loading-card{padding:26px 20px}}"""

ALTAIR_UI_JS = r"""(function(){
  if(window.__altairUIBooted)return;
  window.__altairUIBooted=true;
  const icons={success:'✓',error:'!',warning:'⚠',info:'i',message:'✓'};
  window.altairShowToast=function(message,category='success',duration=4200){
    const container=document.getElementById('altair-toast-container');if(!container||!message)return;
    category=String(category||'info').toLowerCase();if(!['success','error','warning','info','message'].includes(category))category='info';
    const toast=document.createElement('div');toast.className='altair-toast '+category;
    const icon=document.createElement('span');icon.className='altair-toast-icon';icon.textContent=icons[category]||'i';
    const text=document.createElement('div');text.className='altair-toast-message';text.textContent=String(message);
    const close=document.createElement('button');close.className='altair-toast-close';close.type='button';close.setAttribute('aria-label','Dismiss notification');close.textContent='×';
    const remove=()=>{if(!toast.isConnected)return;toast.classList.add('hide');setTimeout(()=>toast.remove(),240)};
    close.addEventListener('click',remove);toast.append(icon,text,close);container.appendChild(toast);setTimeout(remove,duration);
  };
  function readPayload(doc){try{const node=doc.querySelector('#altair-toast-payload');return node?JSON.parse(node.textContent||'[]'):[]}catch(e){return[]}}
  function displayPayload(items){(items||[]).forEach((item,i)=>setTimeout(()=>window.altairShowToast(item.message,item.category,4800),i*180))}
  displayPayload(readPayload(document));
  const overlay=document.getElementById('altair-loading-overlay');
  const loadingMessage=document.getElementById('altair-loading-message');let progressTimer=null;
  const progressMessages=['Searching Google Places and public web sources…','Checking prospect details and contact information…','Removing duplicate results…','Ranking the most relevant prospects…','Preparing your lead cards…'];
  function showLeadLoader(){if(!overlay)return;overlay.classList.add('show');document.body.style.overflow='hidden';if(loadingMessage)loadingMessage.textContent=progressMessages[0];let index=0;clearInterval(progressTimer);progressTimer=setInterval(()=>{index=(index+1)%progressMessages.length;if(loadingMessage)loadingMessage.textContent=progressMessages[index]},2600)}
  function hideLeadLoader(){if(overlay)overlay.classList.remove('show');document.body.style.overflow='';clearInterval(progressTimer);progressTimer=null}
  window.altairHideLeadLoader=hideLeadLoader;
  window.addEventListener('pageshow',hideLeadLoader);

  // Lead search uses normal navigation so the browser displays the returned results,
  // while the overlay remains visible until the new results page loads.
  document.addEventListener('submit',function(event){
    const form=event.target;if(!(form instanceof HTMLFormElement))return;
    if(form.dataset.altairNativeSubmit==='true'){
      if(form.dataset.altairLoading==='true'||/\/ai-leads\/search(?:$|\?)/.test(form.action))showLeadLoader();
      form.querySelectorAll('button[type="submit"],input[type="submit"]').forEach(b=>{b.classList.add('altair-submitting');b.disabled=true});
    }
  },true);

  // AJAX-style saves/updates/deletes: update the main content and keep the page shell.
  document.addEventListener('submit',async function(event){
    const form=event.target;if(!(form instanceof HTMLFormElement)||event.defaultPrevented)return;
    const method=(form.method||'GET').toUpperCase();
    if(method==='GET'||form.dataset.altairNativeSubmit==='true'||form.dataset.noAjax==='true'||form.hasAttribute('target'))return;
    if(form.dataset.altairBusy==='true'){event.preventDefault();return;}
    event.preventDefault();form.dataset.altairBusy='true';
    const submitter=event.submitter;const buttons=Array.from(form.querySelectorAll('button[type="submit"],input[type="submit"]'));
    buttons.forEach(b=>{b.dataset.altairWasDisabled=b.disabled?'1':'0';b.disabled=true;b.classList.add('altair-submitting')});
    try{
      const body=new FormData(form);if(submitter&&submitter.name&&!body.has(submitter.name))body.append(submitter.name,submitter.value||'');
      const response=await fetch(form.action||window.location.href,{method,body,credentials:'same-origin',headers:{'X-Requested-With':'XMLHttpRequest','Accept':'text/html, application/json'}});
      const contentType=(response.headers.get('content-type')||'').toLowerCase();
      if(contentType.includes('application/json')){
        const data=await response.json();window.altairShowToast(data.message||(response.ok?'Saved successfully.':'The action could not be completed.'),data.success?'success':(response.ok?'success':'error'));
        if(data.redirect_url){window.location.assign(data.redirect_url);return;}if(!response.ok)throw new Error(data.message||'Request failed');return;
      }
      const html=await response.text();const parsed=new DOMParser().parseFromString(html,'text/html');
      const messages=readPayload(parsed);const selector='main.main, .main, main, .main-content, #main-content, .page-content';
      const oldRoot=document.querySelector(selector);const newRoot=parsed.querySelector(selector);
      if(!response.ok){window.altairShowToast('The request could not be completed. Please check the form and try again.','error');return;}
      if(!oldRoot||!newRoot){window.location.assign(response.url||window.location.href);return;}
      document.title=parsed.title||document.title;oldRoot.replaceWith(document.importNode(newRoot,true));
      try{const u=new URL(response.url,window.location.href);if(u.origin===window.location.origin)history.replaceState({},'',u.pathname+u.search+u.hash)}catch(e){}
      displayPayload(messages);window.dispatchEvent(new CustomEvent('altair:page-updated',{detail:{url:response.url}}));
      // Re-run initializers that bind handlers to newly rendered page elements.
      document.dispatchEvent(new Event('DOMContentLoaded',{bubbles:true}));
    }catch(error){console.error('Altair AJAX form error:',error);window.altairShowToast('Could not save your changes. Please check your connection and try again.','error')}
    finally{delete form.dataset.altairBusy;buttons.forEach(b=>{b.disabled=b.dataset.altairWasDisabled==='1';b.classList.remove('altair-submitting');delete b.dataset.altairWasDisabled})}
  });
})();"""


def flash(message, category="message"):
    """Keep Flask flash behavior and also queue a toast notification."""
    _flask_flash(message, category)
    try:
        queue = session.get("_altair_ui_toasts", [])
        queue.append({"message": str(message), "category": str(category or "info")})
        session["_altair_ui_toasts"] = queue[-8:]
    except RuntimeError:
        pass


@app.after_request
def altair_ui_inject(response):
    """Embed toast/loading UI directly into HTML responses (no extra files)."""
    try:
        if (response.status_code == 200
                and "text/html" in (response.content_type or "")
                and not response.is_streamed
                and request.endpoint != "static"):
            html = response.get_data(as_text=True)
            toasts = session.pop("_altair_ui_toasts", [])
            session.modified = True
            payload = json.dumps(toasts, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            injection = (
                '<style id="altair-ui-inline-styles">' + ALTAIR_UI_CSS + '</style>'
                '<div id="altair-toast-container" aria-live="polite" aria-atomic="false"></div>'
                '<div id="altair-loading-overlay" role="status" aria-live="polite" aria-label="Loading">'
                '<div class="altair-loading-card"><div class="altair-loader-orbit"></div>'
                '<h2 class="altair-loading-title" id="altair-loading-title">Finding potential customers</h2>'
                '<p class="altair-loading-message" id="altair-loading-message">Searching trusted sources. This may take a moment…</p>'
                '<div class="altair-loading-track"><span></span></div></div></div>'
                '<script type="application/json" id="altair-toast-payload">' + payload + '</script>'
                '<script id="altair-ui-inline-script">' + ALTAIR_UI_JS + '</script>'
            )
            match = re.search(r"</body\s*>", html, flags=re.IGNORECASE)
            if match:
                html = html[:match.start()] + injection + html[match.start():]
                response.set_data(html)
            else:
                response.set_data(html + injection)
    except Exception as ui_error:
        print("ALTAIR UI INJECTION ERROR:", ui_error)
    return response

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


# ================================================================
# OTIS | SUPERVISED SKLEARN CHATBOT
# TF-IDF text features + Logistic Regression intent classifier.
# No OpenAI API, paid model API, or external LLM is used.
# ================================================================

OTIS_TRAINING_DATA = [
    # Greetings
    ("hi", "greeting"), ("hello", "greeting"), ("hey Otis", "greeting"),
    ("good morning", "greeting"), ("good afternoon", "greeting"),
    ("good evening", "greeting"), ("hello there", "greeting"),
    ("hey there", "greeting"), ("how are you", "greeting"),
    ("good day Otis", "greeting"),

    # Thanks
    ("thank you", "thanks"), ("thanks Otis", "thanks"),
    ("thank you for the help", "thanks"), ("that helped me", "thanks"),
    ("great thanks", "thanks"), ("I appreciate your help", "thanks"),
    ("thanks for explaining", "thanks"), ("much appreciated", "thanks"),

    # Help / capability
    ("what can you do", "help"), ("how can you help me", "help"),
    ("help me use this assistant", "help"), ("what can I ask you", "help"),
    ("show me examples of questions", "help"), ("what do you understand", "help"),
    ("how do I use Otis", "help"), ("what business questions can you answer", "help"),

    # Troubleshooting
    ("I have an error in the app", "troubleshooting"),
    ("help me fix this error", "troubleshooting"),
    ("the page is not working", "troubleshooting"),
    ("something is broken in the system", "troubleshooting"),
    ("I cannot save my invoice", "troubleshooting"),
    ("the application crashed", "troubleshooting"),
    ("why am I getting an error message", "troubleshooting"),
    ("help me troubleshoot a technical problem", "troubleshooting"),

    # Revenue
    ("how much revenue did I make", "revenue"),
    ("what is my revenue", "revenue"), ("how much money did my business make", "revenue"),
    ("show me my sales revenue", "revenue"), ("what are my sales", "revenue"),
    ("how much have I earned", "revenue"), ("money made by my business", "revenue"),
    ("show my paid revenue", "revenue"), ("how much income have I collected", "revenue"),
    ("what revenue have I received", "revenue"), ("tell me about my earnings", "revenue"),
    ("how are my sales doing", "revenue"), ("total paid invoice amount", "revenue"),
    ("how much have customers paid me", "revenue"), ("income from paid invoices", "revenue"),

    # Forecast
    ("what will my revenue be next month", "forecast"),
    ("predict my revenue", "forecast"), ("how much will I make next month", "forecast"),
    ("what is my revenue forecast", "forecast"), ("forecast my sales", "forecast"),
    ("what does the model predict", "forecast"), ("estimate future revenue", "forecast"),
    ("show my next month revenue prediction", "forecast"), ("predict future sales", "forecast"),
    ("how much revenue might I earn next month", "forecast"),
    ("give me a sales forecast", "forecast"), ("what is the expected revenue", "forecast"),

    # Expenses
    ("how much are my expenses", "expenses"), ("show me my expenses", "expenses"),
    ("how much money am I spending", "expenses"), ("what are my business expenses", "expenses"),
    ("how much have I spent", "expenses"), ("show total spending", "expenses"),
    ("how much do my costs add up to", "expenses"), ("tell me about my spending", "expenses"),
    ("what are my recorded costs", "expenses"), ("how much have I paid out", "expenses"),
    ("show my expense total", "expenses"), ("are my expenses high", "expenses"),

    # Invoices
    ("how many invoices do I have", "invoices"), ("show me my invoices", "invoices"),
    ("how many invoices are pending", "invoices"), ("how many invoices are overdue", "invoices"),
    ("what invoices have been paid", "invoices"), ("tell me my invoice status", "invoices"),
    ("show paid pending and overdue invoices", "invoices"),
    ("how many bills have I issued", "invoices"), ("which invoices are unpaid", "invoices"),
    ("give me an invoice summary", "invoices"), ("invoice collection status", "invoices"),

    # Cash flow
    ("how much money is outstanding", "cash_flow"),
    ("how much money am I waiting for", "cash_flow"),
    ("what is my cash flow situation", "cash_flow"),
    ("how much money is pending", "cash_flow"), ("how much money is overdue", "cash_flow"),
    ("how can I improve my cash flow", "cash_flow"),
    ("what payments are customers yet to make", "cash_flow"),
    ("how much have customers not paid", "cash_flow"),
    ("show my outstanding payments", "cash_flow"), ("am I waiting for payments", "cash_flow"),
    ("what is owed to my business", "cash_flow"), ("help me understand cashflow", "cash_flow"),

    # Customers
    ("how many customers do I have", "customers"), ("show me my customers", "customers"),
    ("how many clients are there", "customers"), ("tell me about my customers", "customers"),
    ("show my client base", "customers"), ("how many customer records exist", "customers"),
    ("give me a customer summary", "customers"), ("customer information overview", "customers"),
    ("how many clients have I registered", "customers"),

    # Leads
    ("how many leads do I have", "leads"), ("show me my leads", "leads"),
    ("how are my leads performing", "leads"), ("how many prospects are recorded", "leads"),
    ("show potential customers", "leads"), ("give me a lead summary", "leads"),
    ("how many new leads do I have", "leads"), ("how many leads converted", "leads"),
    ("what is my lead conversion rate", "leads"), ("show my prospect pipeline", "leads"),

    # Lead conversion analysis
    ("why are my leads not converting", "lead_conversion_analysis"),
    ("why do leads not become customers", "lead_conversion_analysis"),
    ("how can I convert more leads", "lead_conversion_analysis"),
    ("analyse my lead conversion", "lead_conversion_analysis"),
    ("analyze my sales funnel", "lead_conversion_analysis"),
    ("why are prospects not buying", "lead_conversion_analysis"),
    ("how do I improve lead conversion", "lead_conversion_analysis"),
    ("what is stopping leads from converting", "lead_conversion_analysis"),
    ("review my lead follow up", "lead_conversion_analysis"),

    # Profitability (reported separately from cash flow)
    ("what is my profit this month", "profitability"),
    ("how much profit did I make this month", "profitability"),
    ("show me my profit", "profitability"),
    ("am I making a profit", "profitability"),
    ("what is my net profit", "profitability"),
    ("compare my income and expenses", "profitability"),
    ("did my business make a profit", "profitability"),
    ("how much money did I keep after expenses", "profitability"),
    ("what are my profits this month", "profitability"),
    ("calculate my profit for this month", "profitability"),
    ("profit and loss summary", "profitability"),
    ("is my business profitable", "profitability"),

    # Business health
    ("how is my business doing", "business_health"),
    ("how is my business performing", "business_health"),
    ("how healthy is my business", "business_health"),
    ("what is my business health score", "business_health"),
    ("is my business performing well", "business_health"),
    ("give me a business overview", "business_health"),
    ("analyse my overall business performance", "business_health"),
    ("analyze the health of my company", "business_health"),
    ("how well is my business doing", "business_health"),
    ("review my business performance", "business_health"),

    # Recommendations
    ("what should I do to improve my business", "recommendations"),
    ("give me business advice", "recommendations"),
    ("what should I improve", "recommendations"),
    ("what do you recommend", "recommendations"),
    ("how can I grow my business", "recommendations"),
    ("which areas need attention", "recommendations"),
    ("how can I increase profits", "recommendations"),
    ("how can I reduce business costs", "recommendations"),
    ("what are my business priorities", "recommendations"),
    ("give me practical next steps", "recommendations"),
    ("how can I increase sales", "recommendations"),
    ("what are the biggest risks in my business", "recommendations"),
]

OTIS_QUESTIONS = [question for question, intent in OTIS_TRAINING_DATA]
OTIS_INTENTS = [intent for question, intent in OTIS_TRAINING_DATA]

otis_nlp_model = Pipeline([
    ("tfidf", TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
    )),
    ("classifier", LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        C=4.0,
        random_state=42,
    )),
])

otis_nlp_model.fit(OTIS_QUESTIONS, OTIS_INTENTS)

# Backward-compatible name in case other app sections reference this variable.
altair_nlp_model = otis_nlp_model

print("OTIS SUPERVISED SKLEARN CHATBOT TRAINED")
print("Training examples:", len(OTIS_QUESTIONS))
print("Recognised intents:", len(set(OTIS_INTENTS)))


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

        # Current-month figures used by Otis's profitability answers.
        # These use the dates and statuses recorded in the user's own account.
        cursor.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN status = 'Paid' THEN amount ELSE 0 END), 0) AS paid_revenue
            FROM invoices
            WHERE user_id = %s
              AND YEAR(invoice_date) = YEAR(CURRENT_DATE())
              AND MONTH(invoice_date) = MONTH(CURRENT_DATE())
        """, (user_id,))
        current_month_revenue = cursor.fetchone() or {}

        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE user_id = %s
              AND YEAR(expense_date) = YEAR(CURRENT_DATE())
              AND MONTH(expense_date) = MONTH(CURRENT_DATE())
        """, (user_id,))
        current_month_expenses = cursor.fetchone() or {}

        month_revenue = float(current_month_revenue.get("paid_revenue", 0) or 0)
        month_expenses = float(current_month_expenses.get("total", 0) or 0)
        data["current_month_financials"] = {
            "paid_revenue": round(month_revenue, 2),
            "expenses": round(month_expenses, 2),
            "recorded_difference": round(month_revenue - month_expenses, 2),
        }

   
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
            "Here are Otis's recommendations based on your "
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



# ============================================================
# ALTAIR AI ASSISTANT 2.0
# Conversation handling, stronger intent recognition, and
# transparent business-health / lead-conversion analysis.
# Keep this section after the original engines so these improved
# functions are the active versions used by the existing routes.
# ============================================================

# Preserve the existing tested response engine for its established
# revenue, expense, cash-flow, invoice, customer, and forecast answers.
altair_response_engine_legacy = altair_response_engine


def _altair_normalise_text(value):
    value = str(value or "").lower().strip()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def understand_altair_question(question):
    """
    Predict the user's intent with the supervised scikit-learn classifier.
    Low-confidence predictions are rejected rather than treated as facts.
    """
    if not isinstance(question, str) or not question.strip():
        return {"intent": "unknown", "confidence": 0.0}

    cleaned = _altair_normalise_text(question)
    if not cleaned:
        return {"intent": "unknown", "confidence": 0.0}

    try:
        probabilities = otis_nlp_model.predict_proba([cleaned])[0]
        classes = otis_nlp_model.classes_
        best_index = int(probabilities.argmax())
        intent = str(classes[best_index])
        confidence = float(probabilities[best_index] * 100)

        # This is a practical rejection threshold, not a calibrated probability.
        # A prediction below it is treated as unknown to reduce wrong answers.
        if confidence < 32.0:
            return {"intent": "unknown", "confidence": round(confidence, 2)}

        return {"intent": intent, "confidence": round(confidence, 2)}
    except Exception as exc:
        app.logger.exception("OTIS INTENT CLASSIFICATION ERROR: %s", exc)
        return {"intent": "unknown", "confidence": 0.0}


def generate_business_advice(business_data):
    """Calculate an explainable 0-100 indicator from the available records."""
    data = business_data or {}
    invoices = data.get("invoices") or {}
    leads = data.get("leads") or {}
    expenses = data.get("expenses") or {}
    recurring = data.get("recurring") or {}
    forecast = data.get("forecast") or {}

    def num(source, key):
        try:
            return max(0.0, float((source or {}).get(key, 0) or 0))
        except (TypeError, ValueError, AttributeError):
            return 0.0

    paid = num(invoices, "paid_amount")
    pending = num(invoices, "pending_amount")
    overdue = num(invoices, "overdue_amount")
    invoice_count = int(num(invoices, "total"))
    expense_total = num(expenses, "total")
    monthly_cost = num(recurring, "monthly_cost")
    total_leads = int(num(leads, "total"))
    converted = int(num(leads, "converted"))
    converted = min(converted, total_leads) if total_leads else 0
    conversion = (converted / total_leads * 100) if total_leads else 0.0

    # 30 points: payment collection. Missing invoice data is treated as unknown,
    # not as perfect performance.
    if invoice_count > 0:
        total_invoice_value = paid + pending + overdue
        overdue_share = overdue / total_invoice_value if total_invoice_value else 0
        pending_share = pending / total_invoice_value if total_invoice_value else 0
        collection_score = max(0.0, 30.0 - min(30.0, overdue_share * 60 + pending_share * 15))
    else:
        collection_score = 18.0

    # 25 points: recorded expenses relative to recorded paid invoice revenue.
    if paid > 0:
        expense_ratio = expense_total / paid
        if expense_ratio <= 0.50: expense_score = 25.0
        elif expense_ratio <= 0.75: expense_score = 21.0
        elif expense_ratio <= 1.00: expense_score = 16.0
        elif expense_ratio <= 1.50: expense_score = 9.0
        else: expense_score = 3.0
    else:
        expense_score = 15.0 if expense_total == 0 else 5.0

    # 25 points: recorded lead conversion. No leads means there is not enough
    # evidence to grade conversion, so use a neutral partial score.
    if total_leads > 0:
        if conversion >= 25: lead_score = 25.0
        elif conversion >= 15: lead_score = 20.0
        elif conversion >= 5: lead_score = 14.0
        else: lead_score = 7.0
    else:
        lead_score = 15.0

    # 20 points: recurring costs relative to recent monthly paid revenue.
    monthly_rows = data.get("monthly_revenue") or []
    monthly_values = []
    for row in monthly_rows[-3:]:
        try:
            monthly_values.append(max(0.0, float((row or {}).get("revenue", 0) or 0)))
        except (TypeError, ValueError, AttributeError):
            continue
    if monthly_values:
        avg_monthly_revenue = sum(monthly_values) / len(monthly_values)
        if monthly_cost <= 0:
            recurring_score = 20.0
        elif avg_monthly_revenue <= 0:
            recurring_score = 3.0
        else:
            recurring_ratio = monthly_cost / avg_monthly_revenue
            if recurring_ratio <= 0.30: recurring_score = 20.0
            elif recurring_ratio <= 0.50: recurring_score = 15.0
            elif recurring_ratio <= 0.80: recurring_score = 10.0
            elif recurring_ratio <= 1.00: recurring_score = 5.0
            else: recurring_score = 2.0
    else:
        avg_monthly_revenue = 0.0
        recurring_score = 15.0 if monthly_cost <= 0 else 10.0

    components = {
        "payment_collection": round(collection_score),
        "expense_control": round(expense_score),
        "lead_conversion": round(lead_score),
        "recurring_costs": round(recurring_score),
    }
    health_score = int(round(sum(components.values())))

    issues = []
    if overdue > 0:
        issues.append({"priority": "high", "area": "Cash collection", "finding": f"{overdue:,.2f} is recorded as overdue.", "action": "Contact overdue customers, confirm disputes, and agree on payment dates."})
    if pending > 0:
        issues.append({"priority": "medium", "area": "Pending payments", "finding": f"{pending:,.2f} is still recorded as pending.", "action": "Send reminders before due dates and track each promised payment."})
    if paid > 0 and expense_total > paid:
        issues.append({"priority": "high", "area": "Expense pressure", "finding": "Recorded expenses exceed recorded paid invoice revenue.", "action": "Review expenses and upcoming obligations; this comparison is not a full profit calculation."})
    if total_leads > 0 and conversion < 10:
        issues.append({"priority": "high", "area": "Lead conversion", "finding": f"Recorded lead conversion is {conversion:.1f}%.", "action": "Follow up quickly, qualify prospects, record outcomes, and review lost-lead reasons."})
    if total_leads > converted and total_leads > 0 and int(num(leads, "new_leads")) > 0:
        issues.append({"priority": "medium", "area": "Lead follow-up", "finding": f"{int(num(leads, 'new_leads'))} leads are still marked New.", "action": "Prioritise contacting new leads and update their status after every interaction."})
    if monthly_cost > 0 and monthly_values and avg_monthly_revenue > 0 and monthly_cost > avg_monthly_revenue * 0.5:
        issues.append({"priority": "high", "area": "Recurring costs", "finding": "Active recurring costs are more than half of the recent average monthly paid revenue.", "action": "Review subscriptions, rent, and other recurring commitments before adding new fixed costs."})
    if not issues:
        issues.append({"priority": "info", "area": "Record quality", "finding": "No major issue was detected from the available summary figures.", "action": "Keep invoices, expenses, leads, and customer outcomes updated so trends remain reliable."})

    return {
        "health_score": health_score,
        "health_components": components,
        "priority_issues": issues,
        "paid_revenue": round(paid, 2),
        "overdue_amount": round(overdue, 2),
        "pending_amount": round(pending, 2),
        "expenses": round(expense_total, 2),
        "monthly_recurring": round(monthly_cost, 2),
        "lead_conversion": round(conversion, 1),
        "revenue_prediction": forecast.get("prediction", 0),
        "prediction_confidence": forecast.get("confidence", 0),
    }


def altair_response_engine(intent, business_data, analysis):
    data = business_data or {}
    analysis = analysis or {}
    invoices = data.get("invoices") or {}
    leads = data.get("leads") or {}

    def val(source, key):
        try:
            return float((source or {}).get(key, 0) or 0)
        except (TypeError, ValueError, AttributeError):
            return 0.0

    def count(source, key):
        return int(val(source, key))

    def money(amount):
        return f"{amount:,.2f}"

    if intent == "help":
        return (
            "I'm Otis, your business advisor. I can analyse the records saved in your account, "
            "explain trends, highlight risks, and suggest practical next steps.\n\n"
            "Try asking:\n"
            "• How is my business performing?\n"
            "• What are my biggest business problems?\n"
            "• Why are my leads not converting?\n"
            "• How much revenue is paid, pending, or overdue?\n"
            "• Are my expenses too high?\n"
            "• What is my revenue forecast?\n"
            "• How can I improve cash flow?\n\n"
            "I only know what is recorded in your Altair account; I won't pretend to know an unrecorded reason or event."
        )

    if intent == "troubleshooting":
        return (
            "I can help you work through the issue, but I can't see your screen or server logs from this message alone.\n\n"
            "Please send me:\n"
            "1. The exact error message (copy it from the page or terminal).\n"
            "2. Which page or action caused it (for example, Login, Invoice, Inventory, or AI Lead Finder).\n"
            "3. What you clicked or changed immediately before it happened.\n\n"
            "Remove passwords, API keys, database credentials, and other secrets before sharing logs. I'll use the actual error text to narrow down the cause instead of guessing."
        )

    if intent == "lead_conversion_analysis":
        total = count(leads, "total")
        converted = min(count(leads, "converted"), total)
        new_count = count(leads, "new_leads")
        contacted = count(leads, "contacted")
        interested = count(leads, "interested")
        rate = converted / total * 100 if total else 0.0
        if total == 0:
            return (
                "I can't yet determine why leads are not converting because there are no leads recorded in the data I received.\n\n"
                "Add/import leads and update each lead's status as you contact them. Once there are records, I can compare New, Contacted, Interested, and Converted counts."
            )
        result = (
            "LEAD CONVERSION ANALYSIS\n\n"
            f"Total recorded leads: {total}\n"
            f"New: {new_count}\n"
            f"Contacted: {contacted}\n"
            f"Interested: {interested}\n"
            f"Converted: {converted}\n"
            f"Recorded conversion rate: {rate:.1f}%\n\n"
        )
        observations = []
        if new_count:
            observations.append(f"{new_count} lead(s) are still marked New, which points to a follow-up queue to work through.")
        if contacted + interested > converted:
            observations.append("There are leads recorded as Contacted/Interested that have not been marked Converted. The status totals alone do not reveal why they did not buy.")
        if rate < 10:
            observations.append("The recorded conversion rate is low enough to justify reviewing lead quality, response time, offer fit, pricing, trust signals, and follow-up consistency.")
        if not observations:
            observations.append("The saved status counts do not show an obvious follow-up bottleneck. Review recent lost deals and compare conversion by lead source to find more specific patterns.")
        result += "What the records suggest:\n" + "\n".join(f"• {item}" for item in observations)
        result += (
            "\n\nRecommended next steps:\n"
            "1. Contact New leads promptly and log the outcome.\n"
            "2. Give interested prospects a clear next step, quote, or meeting.\n"
            "3. Record a reason when a lead is lost (price, timing, no response, poor fit, or competitor).\n"
            "4. Compare conversion by source and service after enough outcomes have been recorded.\n\n"
            "Important: these are diagnostic possibilities, not confirmed causes. Altair cannot infer a buyer's reason unless it is recorded."
        )
        return result

    if intent == "business_health":
        score = int(val(analysis, "health_score"))
        components = analysis.get("health_components") or {}
        issues = analysis.get("priority_issues") or []
        description = (
            "strong recorded indicators" if score >= 80 else
            "a mixed picture with areas to monitor" if score >= 60 else
            "several areas that may need attention"
        )
        component_lines = [
            f"• Payment collection: {components.get('payment_collection', 'N/A')}/30",
            f"• Expense control: {components.get('expense_control', 'N/A')}/25",
            f"• Lead conversion: {components.get('lead_conversion', 'N/A')}/25",
            f"• Recurring costs: {components.get('recurring_costs', 'N/A')}/20",
        ]
        issue_lines = [f"• {item.get('area', 'Business')}: {item.get('finding', '')} Next step: {item.get('action', '')}" for item in issues[:4]]
        return (
            "BUSINESS HEALTH CHECK\n\n"
            f"Otis business-health indicator: {score}/100\n"
            f"Overall reading: Your recorded figures show {description}.\n\n"
            "Score breakdown (each component is weighted):\n" + "\n".join(component_lines) +
            "\n\nRecorded figures:\n"
            f"• Paid invoice revenue: {money(val(invoices, 'paid_amount'))}\n"
            f"• Pending invoices: {money(val(invoices, 'pending_amount'))}\n"
            f"• Overdue invoices: {money(val(invoices, 'overdue_amount'))}\n"
            f"• Recorded expenses: {money(val(data.get('expenses'), 'total'))}\n"
            f"• Leads converted: {count(leads, 'converted')} of {count(leads, 'total')}\n\n"
            "Main areas to review:\n" + "\n".join(issue_lines) +
            "\n\nThis is an internal operational indicator based on the records available to Altair, not a formal accounting, credit, or investment assessment. Missing or incomplete records can change the score."
        )

    if intent == "profitability":
        monthly = data.get("current_month_financials") or {}
        month_revenue = val(monthly, "paid_revenue")
        month_expenses = val(monthly, "expenses")
        difference = val(monthly, "recorded_difference")
        label = "positive recorded difference" if difference > 0 else (
            "negative recorded difference" if difference < 0 else "break-even recorded difference"
        )
        return (
            "CURRENT-MONTH PROFITABILITY SNAPSHOT\\n\\n"
            f"Paid invoice revenue recorded this month: {money(month_revenue)}\\n"
            f"Expenses recorded this month: {money(month_expenses)}\\n"
            f"Revenue minus recorded expenses: {money(difference)}\\n\\n"
            f"The current records show a {label}. This is a simple operational estimate, "
            "not a formal accounting profit figure: it excludes any income, costs, taxes, "
            "or adjustments that have not been entered in Altair."
        )

    if intent == "recommendations":
        issues = analysis.get("priority_issues") or []
        lines = []
        for item in issues[:5]:
            lines.append(f"{len(lines)+1}. {item.get('area', 'Priority')} — {item.get('finding', '')} Action: {item.get('action', '')}")
        if not lines:
            lines = ["Keep your invoices, expenses, lead statuses, and customer records up to date; revisit these indicators regularly."]
        return "OTIS BUSINESS PRIORITIES\n\n" + "\n\n".join(lines) + "\n\nThese priorities are based on the data currently recorded in your account."

    # Existing established intents keep their previous answer logic.
    return altair_response_engine_legacy(intent, business_data, analysis)


# ALTAIR AI CHAT API

# ================================================================
# OTIS APPLICATION KNOWLEDGE + SAFE RECORD SEARCH
# ================================================================
OTIS_APP_KNOWLEDGE = {
    "dashboard": ("Dashboard", "/", "Shows a business overview, performance indicators, forecast information, recent activity, and Otis advice when data is available."),
    "customer": ("Customers", "/customer", "View and manage customer names, emails, phone numbers, company details, addresses, status, notes, and available customer history."),
    "invoice": ("Invoices", "/invoice", "Create and review invoices with invoice number, customer, item description, dates, amount, status, and notes. Otis can summarise paid, pending, and overdue amounts."),
    "money management": ("Money Management", "/items", "Review recorded expenses, investments, and recurring payments, including categories, amounts, and payment schedules."),
    "inventory": ("Inventory", "/items", "Inventory records can include item name, SKU, category, type, description, supplier, quantity, low-stock level, cost price, selling price, and status."),
    "lead": ("AI Lead Finder", "/ai-leads", "Manage potential customers and saved lead details such as company, industry, location, website, email, phone, contact person, source, status, score, and notes."),
    "company profile": ("Company Profile", "/company-setup", "Manage company name, industry, specialisation, description, services/products, contact details, website, address, city, country, and logo."),
    "help support": ("Help & Support", "/help-support", "Submit a support request. For technical troubleshooting, provide the exact error and the page/action that caused it. Never share passwords or API keys."),
    "settings": ("Settings", "/settings", "Manage available preferences, including invoice payment terms and payment details where configured."),
    "otis": ("Otis Business Advisor", "/", "Otis can summarise recorded revenue, expenses, invoices, customers, leads, cash flow, forecasts, and business indicators. Its answers depend on the saved data and implemented features; it must not invent missing facts."),
}

def _otis_norm(value):
    value = str(value or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9@._+\-\s]", " ", value)).strip()

def _otis_knowledge_answer(message):
    q = _otis_norm(message)
    general_product_question = any(x in q for x in (
        "what can altair", "what can this app", "what features",
        "what is altair business suite", "what can otis do",
        "how do i use altair", "how do i use this app",
        "how does altair work", "show me the app", "help me navigate",
        "where can i find", "which page", "what page",
        "how do i access", "how do i open", "how do i use",
        "how to use", "where is the", "tell me about the ", "explain the "
    ))
    if general_product_question:
        return (
            "I can help you navigate Altair Business Suite and find saved records.\n\n"
            "MAIN AREAS:\n"
            "• Dashboard — business overview and recent activity (/)\n"
            "• Customers — customer records (/customer)\n"
            "• Invoices — billing and payment status (/invoice)\n"
            "• Money Management — expenses, investments, recurring payments (/items)\n"
            "• Inventory — stock and product records (Inventory area)\n"
            "• AI Lead Finder — prospects and lead statuses (/ai-leads)\n"
            "• Company Profile — company details (/company-setup)\n"
            "• Help & Support — support requests (/help-support)\n"
            "• Settings — available preferences (/settings)\n\n"
            "Ask me to find a specific invoice, customer, lead, inventory item, expense, investment, or recurring payment."
        )
    # Ordinary questions about money or records should reach the live data engine.
    documentation_cues = (
        "page", "feature", "section", "tab", "where", "how do i",
        "how to", "what is the", "what does the", "explain the",
        "tell me about the", "help me use", "open the"
    )
    if not any(cue in q for cue in documentation_cues):
        return None
    for key in sorted(OTIS_APP_KNOWLEDGE, key=len, reverse=True):
        if key in q:
            title, path, description = OTIS_APP_KNOWLEDGE[key]
            return f"{title}\n\n{description}\n\nOpen this area: {path}\n\nYou can also ask: 'Find {key} [name or number]'."
    return None

def _otis_is_record_search(message):
    q = _otis_norm(message)
    # Page/navigation questions belong to the documentation helper, not database search.
    if any(word in q for word in (" page", " feature", " section", " tab", "navigate", "menu")):
        return False
    return any(v in q for v in (
        "find ", "search ", "look for ", "look up ", "locate ",
        "show me the record for ", "where is my "
    ))

def _otis_search_records(user_id, message):
    """Search the signed-in user's saved records; all SQL uses parameters."""
    q = _otis_norm(message)
    for phrase in (
        "please", "can you", "could you", "find", "search", "look for",
        "look up", "locate", "show me", "the record for", "where is",
        "my", "the", "invoice", "invoices", "customer", "customers",
        "client", "clients", "lead", "leads", "prospect", "prospects",
        "inventory", "stock", "item", "items", "expense", "expenses",
        "investment", "investments", "recurring payment", "recurring payments",
        "payment", "payments", "for", "named", "called", "number"
    ):
        q = re.sub(r"\b" + re.escape(phrase) + r"\b", " ", q)
    q = re.sub(r"\s+", " ", q).strip(" .?!")
    if not q:
        return "What should I look for? Include a name, invoice number, company, email, item name, or SKU. Example: 'Find invoice INV-1004'."

    term = f"%{q}%"
    specs = [
        ("Invoice", """SELECT invoice_number AS name, CONCAT(COALESCE(customer_name,''),' ',COALESCE(customer_email,''),' ',COALESCE(item_name,'')) AS detail, status, amount, invoice_date AS record_date FROM invoices WHERE user_id=%s AND (invoice_number LIKE %s OR customer_name LIKE %s OR customer_email LIKE %s OR item_name LIKE %s OR status LIKE %s) ORDER BY invoice_date DESC LIMIT 5""", 5),
        ("Customer", """SELECT name, CONCAT(COALESCE(email,''),' ',COALESCE(phone,''),' ',COALESCE(company_name,''),' ',COALESCE(city,''),' ',COALESCE(country,'')) AS detail, status, total_spent AS amount, created_at AS record_date FROM customers WHERE user_id=%s AND (name LIKE %s OR email LIKE %s OR phone LIKE %s OR company_name LIKE %s OR city LIKE %s OR country LIKE %s) ORDER BY id DESC LIMIT 5""", 6),
        ("Lead", """SELECT company_name AS name, CONCAT(COALESCE(contact_person,''),' ',COALESCE(email,''),' ',COALESCE(phone,''),' ',COALESCE(location,''),' ',COALESCE(industry,'')) AS detail, lead_status AS status, lead_score AS amount, NULL AS record_date FROM leads WHERE user_id=%s AND (company_name LIKE %s OR contact_person LIKE %s OR email LIKE %s OR phone LIKE %s OR location LIKE %s OR industry LIKE %s) ORDER BY id DESC LIMIT 5""", 6),
        ("Inventory item", """SELECT item_name AS name, CONCAT(COALESCE(sku,''),' ',COALESCE(category,''),' ',COALESCE(supplier,''),' ',COALESCE(description,'')) AS detail, status, quantity AS amount, NULL AS record_date FROM inventory WHERE user_id=%s AND (item_name LIKE %s OR sku LIKE %s OR category LIKE %s OR supplier LIKE %s OR description LIKE %s) ORDER BY id DESC LIMIT 5""", 5),
        ("Expense", """SELECT expense_name AS name, CONCAT(COALESCE(category,''),' ',COALESCE(description,'')) AS detail, payment_method AS status, amount, expense_date AS record_date FROM expenses WHERE user_id=%s AND (expense_name LIKE %s OR category LIKE %s OR description LIKE %s) ORDER BY expense_date DESC LIMIT 5""", 3),
        ("Investment", """SELECT investment_name AS name, CONCAT(COALESCE(category,''),' ',COALESCE(description,'')) AS detail, status, amount, investment_date AS record_date FROM investments WHERE user_id=%s AND (investment_name LIKE %s OR category LIKE %s OR description LIKE %s) ORDER BY investment_date DESC LIMIT 5""", 3),
        ("Recurring payment", """SELECT payment_name AS name, CONCAT(COALESCE(category,''),' ',COALESCE(frequency,''),' ',COALESCE(description,'')) AS detail, status, amount, next_payment_date AS record_date FROM recurring_payments WHERE user_id=%s AND (payment_name LIKE %s OR category LIKE %s OR frequency LIKE %s OR description LIKE %s) ORDER BY next_payment_date ASC LIMIT 5""", 4),
    ]
    db = cursor = None
    results = []
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        for label, sql, field_count in specs:
            cursor.execute(sql, tuple([user_id] + [term] * field_count))
            for row in cursor.fetchall() or []:
                results.append((label, row))
                if len(results) >= 12:
                    break
            if len(results) >= 12:
                break
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()
    if not results:
        return f"I couldn't find a saved record matching '{q}'. Try a shorter name, invoice number, email, company name, or SKU. I only search records already saved in your account."
    output = [f"Saved records matching '{q}':"]
    for label, row in results:
        detail = str(row.get("detail") or "").strip()
        status = str(row.get("status") or "").strip()
        amount = row.get("amount")
        dt = row.get("record_date")
        extra = f", status: {status}" if status else ""
        if amount is not None and label in {"Invoice", "Expense", "Investment", "Recurring payment"}:
            try:
                extra += f", amount: {float(amount):,.2f}"
            except (TypeError, ValueError):
                pass
        if dt:
            extra += f", date: {dt}"
        if detail:
            extra += f", details: {detail[:120]}"
        output.append(f"• {label}: {row.get('name') or 'Unnamed'}{extra}")
    output.append("\nSearch was limited to records belonging to your signed-in account.")
    return "\n".join(output)



@app.route("/api/ai/chat", methods=["POST"])
def altair_ai_chat():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please login first."}), 401

    user_id = session["user_id"]
    try:
        body = request.get_json(silent=True) or {}
        message = str(body.get("message", "")).strip()
        if not message:
            return jsonify({"success": False, "message": "Please enter a question."}), 400
        if len(message) > 3000:
            return jsonify({"success": False, "message": "Please keep your message under 3,000 characters."}), 400

        if _otis_is_record_search(message):
            reply = _otis_search_records(user_id, message)
            return jsonify({"success": True, "reply": reply, "intent": "record_search", "confidence": 100.0})

        knowledge_reply = _otis_knowledge_answer(message)
        if knowledge_reply:
            return jsonify({"success": True, "reply": knowledge_reply, "intent": "app_knowledge", "confidence": 100.0})

        # Handle simple conversation without requiring a database query.
        understanding = understand_altair_question(message)
        intent = understanding.get("intent", "unknown")
        confidence = float(understanding.get("confidence", 0) or 0)

        if intent == "greeting":
            hour = datetime.now().hour
            if 5 <= hour < 12:
                time_greeting = "Good morning"
            elif 12 <= hour < 17:
                time_greeting = "Good afternoon"
            else:
                time_greeting = "Good evening"
            return jsonify({
                "success": True,
                "reply": f"{time_greeting}! 👋 I'm Otis, your business advisor. I can help you understand business health, revenue, cash flow, expenses, invoices, customers, lead conversion, and practical next steps. What would you like to look at?",
                "intent": intent,
                "confidence": confidence,
            })

        if intent == "thanks":
            return jsonify({
                "success": True,
                "reply": "You're welcome! I'm here whenever you want to review your numbers or work through a business question.",
                "intent": intent,
                "confidence": confidence,
            })

        # General help and troubleshooting do not require private business records.
        if intent in {"help", "troubleshooting"}:
            reply = altair_response_engine(intent, {}, {})
            return jsonify({"success": True, "reply": reply, "intent": intent, "confidence": round(confidence, 2)})

        if intent == "unknown":
            reply = (
                "I want to make sure I understand what you mean rather than give you a made-up answer. "
                "Could you rephrase the question or tell me which part of the business you mean?\n\n"
                "I can help with:\n"
                "• Business health and the biggest risks\n"
                "• Revenue, expenses, and cash flow\n"
                "• Paid, pending, and overdue invoices\n"
                "• Customer and lead performance\n"
                "• Why leads may not be converting\n"
                "• Revenue forecasting and practical recommendations\n\n"
                "If you mean an application error, paste the exact error message and tell me which page produced it."
            )
            return jsonify({"success": True, "reply": reply, "intent": "unknown", "confidence": round(confidence, 2)})

        # Only fetch private business records after the authenticated session is verified.
        # get_business_ai_data independently checks the current company ownership.
        business_data = get_business_ai_data(user_id)
        analysis = generate_business_advice(business_data)

        reply = altair_response_engine(intent, business_data, analysis)
        return jsonify({
            "success": True,
            "reply": reply,
            "intent": intent,
            "confidence": round(confidence, 2),
        })

    except PermissionError as exc:
        print("ALTAIR AI ACCESS CHECK:", exc)
        return jsonify({"success": False, "message": "Your account does not have an accessible company profile. Please check your company setup."}), 403
    except Exception as exc:
        print("ALTAIR AI CHAT ERROR:", exc)
        return jsonify({"success": False, "message": "Otis could not process your question right now. Please try again; if it continues, share the server error log without passwords or API keys."}), 500





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



# HELP & SUPPORT CENTRE
@app.route("/help-support", methods=["GET", "POST"])
def help_support():
    """Help centre and user-owned support tickets."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    db = None
    cursor = None
    company = None
    tickets = []

    # The table is created automatically so no separate SQL import is required.
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                ticket_number VARCHAR(32) NOT NULL UNIQUE,
                user_id BIGINT NOT NULL,
                company_id BIGINT NULL,
                subject VARCHAR(180) NOT NULL,
                category VARCHAR(60) NOT NULL,
                priority VARCHAR(20) NOT NULL DEFAULT 'Normal',
                description TEXT NOT NULL,
                contact_email VARCHAR(255) NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'Open',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_support_user_created (user_id, created_at),
                INDEX idx_support_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
            SELECT * FROM companies WHERE user_id = %s LIMIT 1
        """, (user_id,))
        company = cursor.fetchone()

        if not company:
            if request.method == "POST":
                flash("Please complete your company profile before submitting a support ticket.", "warning")
            else:
                return redirect(url_for("company_setup"))

        if request.method == "POST":
            subject = (request.form.get("subject") or "").strip()
            category = (request.form.get("category") or "General Enquiry").strip()
            priority = (request.form.get("priority") or "Normal").strip()
            description = (request.form.get("description") or "").strip()
            contact_email = (request.form.get("contact_email") or session.get("user_email") or "").strip()

            allowed_categories = {
                "Technical Issue", "Account & Login", "Billing", "AI Features",
                "Customers & Invoices", "Data & Reports", "General Enquiry", "Security Concern"
            }
            allowed_priorities = {"Low", "Normal", "High", "Urgent"}

            if not company:
                pass
            elif not subject or not description:
                flash("Please enter both a subject and a description.", "error")
            elif len(subject) > 180:
                flash("The subject must be 180 characters or fewer.", "error")
            elif len(description) > 12000:
                flash("Please keep the description under 12,000 characters.", "error")
            elif category not in allowed_categories or priority not in allowed_priorities:
                flash("Please choose a valid category and priority.", "error")
            elif len(contact_email) > 255:
                flash("Please enter a valid contact email address.", "error")
            else:
                # Use a unique ticket reference and bind every user value as SQL parameters.
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM support_tickets")
                next_id_row = cursor.fetchone() or {}
                ticket_number = "ALT-" + datetime.now().strftime("%y%m%d") + "-" + str(next_id_row.get("next_id", 1)).zfill(5)
                company_id = company.get("id") if company else None
                cursor.execute("""
                    INSERT INTO support_tickets
                        (ticket_number, user_id, company_id, subject, category, priority,
                         description, contact_email, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Open')
                """, (ticket_number, user_id, company_id, subject, category, priority,
                      description, contact_email or None))
                db.commit()
                flash("Support ticket " + ticket_number + " was submitted successfully.", "success")
                return redirect(url_for("help_support", _anchor="my-tickets"))

        # Strictly limit the ticket list to the authenticated user.
        cursor.execute("""
            SELECT ticket_number, subject, category, priority, description,
                   contact_email, status, created_at, updated_at
            FROM support_tickets
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (user_id,))
        tickets = cursor.fetchall() or []

    except Exception as exc:
        if db:
            try:
                db.rollback()
            except Exception:
                pass
        app.logger.exception("Help & Support page failed")
        flash("The Help & Support service could not load right now. Please try again later.", "error")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

    return render_template(
        "help_support.html",
        company=company,
        tickets=tickets,
        user_name=session.get("user_name"),
        user_email=session.get("user_email"),
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



# COMING SOON: ACCOUNT, BILLING, AND BUSINESS MANAGEMENT MODULES
@app.route("/coming-soon/<feature>")
def coming_soon(feature):
    if "user_id" not in session:
        return redirect(url_for("login"))

    features = {
        "subscription-plans": {"title": "Subscription Plans", "icon": "👑", "category": "ACCOUNT & BILLING", "description": "Explore subscription tiers and choose the features that fit your business.", "status": "Coming Soon"},
        "billing-payments": {"title": "Billing & Payments", "icon": "💰", "category": "ACCOUNT & BILLING", "description": "Manage your Altair subscription payments and billing details in one place.", "status": "Coming Soon"},
        "billing-history": {"title": "Billing History", "icon": "🧾", "category": "ACCOUNT & BILLING", "description": "Review previous subscription invoices, receipts, and payment records.", "status": "Coming Soon"},
        "usage-limits": {"title": "Usage & Limits", "icon": "📊", "category": "ACCOUNT & BILLING", "description": "Track plan usage, limits, and available allowances for your account.", "status": "Coming Soon"},
        "employees-team": {"title": "Employees & Team", "icon": "🧑‍💼", "category": "BUSINESS MANAGEMENT", "description": "Invite teammates, organise roles, and manage access to your company workspace.", "status": "Coming Soon"},
        "documents-reports": {"title": "Documents & Reports", "icon": "📄", "category": "BUSINESS MANAGEMENT", "description": "Keep important business documents and downloadable reports organised.", "status": "Coming Soon"},
        "notifications": {"title": "Notifications", "icon": "🔔", "category": "BUSINESS MANAGEMENT", "description": "Control business alerts, reminders, and important account notifications.", "status": "Coming Soon"},
        "integrations": {"title": "Integrations", "icon": "🔗", "category": "BUSINESS MANAGEMENT", "description": "Connect Altair with the tools and services your business already uses.", "status": "Coming Soon"},
    }

    feature_data = features.get(feature)
    if not feature_data:
        abort(404)

    db = None
    cursor = None
    company = None
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM companies WHERE user_id = %s LIMIT 1",
            (session["user_id"],)
        )
        company = cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

    if company is None:
        return redirect(url_for("company_setup"))

    template_by_feature = {
        "subscription-plans": "subscription_plans.html",
        "billing-payments": "billing_payments.html",
        "billing-history": "billing_history.html",
        "usage-limits": "usage_limits.html",
        "employees-team": "employees_team.html",
        "documents-reports": "documents_reports.html",
        "notifications": "notifications.html",
        "integrations": "integrations.html",
    }

    return render_template(
        template_by_feature[feature],
        company=company,
        feature=feature_data,
        feature_slug=feature,
        user_name=session.get("user_name"),
        user_email=session.get("user_email"),
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

                # Upload to Cloudinary so the logo persists across
                # Render deployments/restarts, just like Company Setup.
                try:
                    upload_result = cloudinary.uploader.upload(
                        logo,
                        folder="altair_business_suite/company_logos",
                        public_id=f"company_{user_id}",
                        overwrite=True,
                        resource_type="image"
                    )

                    logo_url = upload_result.get("secure_url")

                    if not logo_url:
                        raise RuntimeError(
                            "Cloudinary did not return a secure logo URL."
                        )

                    app.logger.info(
                        "Company logo uploaded to Cloudinary for user_id=%s",
                        user_id
                    )

                except Exception as upload_error:
                    app.logger.exception(
                        "SETTINGS CLOUDINARY LOGO UPLOAD ERROR: %s",
                        upload_error
                    )

                    flash(
                        "Could not upload the company logo. Please check "
                        "your Cloudinary environment variables and try again.",
                        "error"
                    )

                    return redirect(url_for("settings"))

            
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


@app.route("/ai-leads/<int:lead_id>/edit", methods=["POST"])
def edit_ai_lead(lead_id):

    # Require login
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Collect the edited information
    company_name = request.form.get("company_name", "").strip()
    industry = request.form.get("industry", "").strip()
    location = request.form.get("location", "").strip()
    contact_person = request.form.get("contact_person", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    website = request.form.get("website", "").strip()
    source = request.form.get("source", "Manual").strip()
    lead_status = request.form.get("lead_status", "New").strip()
    ai_analysis = request.form.get("ai_analysis", "").strip()
    ai_reason = request.form.get("ai_reason", "").strip()
    ai_message = request.form.get("ai_message", "").strip()
    notes = request.form.get("notes", "").strip()
    google_place_id = request.form.get("google_place_id", "").strip()

    # Validate the company name
    if not company_name:
        flash("Company name is required.", "error")
        return redirect(url_for("ai_leads"))

    # Validate lead score
    try:
        score_text = request.form.get("lead_score", "0").strip()
        lead_score = int(score_text or 0)

        if not 0 <= lead_score <= 100:
            raise ValueError

    except ValueError:
        flash("Lead score must be between 0 and 100.", "error")
        return redirect(url_for("ai_leads"))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # SECURITY:
        # Only allow editing leads owned by the logged-in user.
        cursor.execute(
            """
            SELECT id
            FROM leads
            WHERE id = %s AND user_id = %s
            """,
            (lead_id, user_id)
        )

        if not cursor.fetchone():
            flash("Lead not found or you do not have permission to edit it.", "error")
            return redirect(url_for("ai_leads"))

        # Save the changes
        cursor.execute(
            """
            UPDATE leads
            SET
                company_name = %s,
                industry = %s,
                location = %s,
                contact_person = %s,
                email = %s,
                phone = %s,
                website = %s,
                source = %s,
                lead_status = %s,
                lead_score = %s,
                ai_analysis = %s,
                ai_reason = %s,
                ai_message = %s,
                notes = %s,
                google_place_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
            """,
            (
                company_name,
                industry,
                location,
                contact_person,
                email,
                phone,
                website,
                source,
                lead_status,
                lead_score,
                ai_analysis,
                ai_reason,
                ai_message,
                notes,
                google_place_id,
                lead_id,
                user_id
            )
        )

        conn.commit()

        flash("Lead updated successfully!", "success")

    except Exception as e:
        if conn:
            conn.rollback()

        print("EDIT AI LEAD ERROR:", e)

        flash("Could not update the lead. Check the server logs.", "error")

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

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

    prospect_type = request.form.get("prospect_type", "businesses").strip().lower()
    if prospect_type not in {"businesses", "people", "both"}:
        prospect_type = "businesses"


    
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
            10
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


    brave_search_api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()

    if prospect_type == "businesses" and not GOOGLE_PLACES_API_KEY:
        flash("Google Places API key is not configured for business searches.", "error")
        return redirect(url_for("ai_leads"))

    if prospect_type == "people" and not brave_search_api_key:
        flash("Individual-prospect search needs BRAVE_SEARCH_API_KEY. Add it to your environment to search public web results for people-related requests.", "error")
        return redirect(url_for("ai_leads"))

    if prospect_type == "both" and not GOOGLE_PLACES_API_KEY and not brave_search_api_key:
        flash("Configure GOOGLE_PLACES_API_KEY for business leads and/or BRAVE_SEARCH_API_KEY for public web search of individual prospects.", "error")
        return redirect(url_for("ai_leads"))


    
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


    
    # DISCOVER PROSPECTS FROM THE SELECTED SOURCE(S)
    # Google Places provides business listings only. For individual prospects,
    # use Brave Search API to find public web pages that may show service requests.
    google_places = []
    source_errors = []

    if prospect_type in ("businesses", "both") and GOOGLE_PLACES_API_KEY:
        places_url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
            "X-Goog-FieldMask": ",".join([
                "places.id", "places.displayName", "places.formattedAddress",
                "places.websiteUri", "places.nationalPhoneNumber",
                "places.internationalPhoneNumber", "places.types",
                "places.businessStatus", "places.googleMapsUri"
            ])
        }
        try:
            response = requests.post(
                places_url, headers=headers,
                json={"textQuery": search_query, "pageSize": max_results}, timeout=30
            )
            print("GOOGLE PLACES STATUS:", response.status_code)
            if response.status_code == 200:
                for place in response.json().get("places", []):
                    place["_prospect_type"] = "Business / Organization"
                    place["_source_type"] = "Google Places"
                    google_places.append(place)
            else:
                source_errors.append("Google Places returned an error; business results may be missing.")
                print("GOOGLE PLACES ERROR BODY:", response.text[:500])
        except requests.RequestException as exc:
            source_errors.append("Could not connect to Google Places.")
            print("GOOGLE PLACES API ERROR:", type(exc).__name__, str(exc))
    elif prospect_type in ("businesses", "both") and not GOOGLE_PLACES_API_KEY:
        source_errors.append("Business search is unavailable because GOOGLE_PLACES_API_KEY is not configured.")

    if prospect_type in ("people", "both") and brave_search_api_key:
        from hashlib import sha256
        people_query_parts = [f'("looking for" OR "need" OR "recommend" OR "seeking") {services}', location]
        if industry:
            people_query_parts.append(industry)
        if keywords:
            people_query_parts.append(keywords)
        people_query = " ".join(part for part in people_query_parts if part).strip()
        try:
            brave_response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"Accept": "application/json", "X-Subscription-Token": brave_search_api_key},
                params={"q": people_query, "count": min(max_results, 10), "safesearch": "moderate"},
                timeout=20
            )
            print("BRAVE SEARCH STATUS:", brave_response.status_code)
            if brave_response.status_code == 200:
                web_results = (brave_response.json().get("web") or {}).get("results", [])
                for item in web_results:
                    link = (item.get("url") or "").strip()
                    if not link:
                        continue
                    snippet = (item.get("description") or "").strip()
                    title = (item.get("title") or "Public profile / request")[:250]
                    # Use only data actually returned by the search API; do not
                    # infer a person's identity or invent contact details.
                    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", snippet, re.I)
                    phone_match = re.search(r"(?:\+?\d[\d ()-]{7,}\d)", snippet)
                    synthetic_id = "web_" + sha256(link.encode("utf-8")).hexdigest()[:32]
                    google_places.append({
                        "id": synthetic_id,
                        "displayName": {"text": title},
                        "formattedAddress": "",
                        "websiteUri": link,
                        "nationalPhoneNumber": phone_match.group(0).strip() if phone_match else "",
                        "internationalPhoneNumber": "",
                        "types": ["individual_prospect"],
                        "businessStatus": "",
                        "googleMapsUri": link,
                        "_prospect_type": "Individual / Public Web Result",
                        "_source_type": "Brave Web Search",
                        "_evidence_text": snippet,
                        "_person_search_query": people_query,
                        "_email_from_snippet": email_match.group(0).lower() if email_match else ""
                    })
            else:
                source_errors.append("Brave Search returned an error; individual public-web results may be missing.")
                print("BRAVE SEARCH ERROR BODY:", brave_response.text[:500])
        except requests.RequestException as exc:
            source_errors.append("Could not connect to Brave Search.")
            print("BRAVE SEARCH ERROR:", type(exc).__name__, str(exc))
    elif prospect_type in ("people", "both") and not brave_search_api_key:
        source_errors.append("Individual search is not configured. Add BRAVE_SEARCH_API_KEY to enable public web search for people-related requests.")

    if source_errors:
        for source_error in source_errors:
            flash(source_error, "error" if prospect_type == "people" else "warning")

    # Preserve source-specific results while removing duplicate URLs/IDs.
    deduped_results = []
    seen_result_ids = set()
    for result in google_places:
        result_id = result.get("id") or result.get("googleMapsUri") or result.get("websiteUri")
        if result_id and result_id not in seen_result_ids:
            seen_result_ids.add(result_id)
            deduped_results.append(result)
    google_places = deduped_results[:max_results * (2 if prospect_type == "both" else 1)]

    # PROCESS GOOGLE RESULTS
    # Fetch existing lead statuses in ONE database query rather than opening
    # a separate MySQL connection for every Google result. This reduces the
    # chance of a slow search hitting Gunicorn's worker timeout.
    place_ids = [place.get("id") for place in google_places if place.get("id")]
    existing_lead_statuses = {}

    if place_ids:
        status_db = status_cursor = None
        try:
            status_db = get_db_connection()
            status_cursor = status_db.cursor(dictionary=True)
            placeholders = ",".join(["%s"] * len(place_ids))
            status_cursor.execute(
                f"SELECT google_place_id, lead_status FROM leads "
                f"WHERE user_id = %s AND google_place_id IN ({placeholders})",
                tuple([user_id] + place_ids)
            )
            for row in status_cursor.fetchall():
                existing_lead_statuses[row.get("google_place_id")] = (row.get("lead_status") or "").lower()
        except Exception as exc:
            # Search should still work if status enrichment fails.
            print("BATCH LEAD STATUS LOOKUP ERROR:", type(exc).__name__, str(exc))
        finally:
            if status_cursor:
                status_cursor.close()
            if status_db:
                status_db.close()

    google_results = []
    try:
        seller_profile = get_company_for_user(user_id) or {}
    except Exception as exc:
        print("LEAD OUTREACH PROFILE LOOKUP ERROR:", type(exc).__name__, str(exc))
        seller_profile = {}
    sender_name = (seller_profile.get("company_name") or session.get("user_name") or "our team").strip()

    for place in google_places:


        
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

        # Google Places has no email field; look for a publicly listed
        # email on the business's own website when a website is available.
        business_email = place.get("_email_from_snippet") or (find_public_business_email(website) if place.get("_source_type", "Google Places") == "Google Places" else "")


        
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

            "email":
                business_email,

            "phone":
                phone,

            "industry":
                industry_name,

            "types":
                types,

            "business_status":
                business_status,

            "google_maps_url":
                google_maps_url,

            "source_url":
                google_maps_url,

            "prospect_type": place.get("_prospect_type", "Business / Organization"),
            "source_type": place.get("_source_type", "Google Places"),
            "evidence_text": place.get("_evidence_text", ""),
            "services_offered": "",

            # Cached from the single batch query above.
            "_not_contacted_or_converted": (
                existing_lead_statuses.get(place.get("id"))
                not in ("contacted", "converted")
            ),
            "_prospect_type": place.get("_prospect_type", "Business / Organization"),
            "_source_type": place.get("_source_type", "Google Places"),
            "evidence_text": place.get("_evidence_text", ""),
            "prospect_type": place.get("_prospect_type", "Business / Organization")
        }


        
        # CHECK FOR COMPETITOR
        

        if potential_lead.get("prospect_type") == "Business / Organization" and is_likely_competitor(potential_lead, services):

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

            keywords=keywords,

            user_id=user_id,
            sender_name=sender_name
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
                ),

            "score_breakdown":
                qualification.get(
                    "score_breakdown",
                    {}
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

        search_prospect_type=prospect_type,

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


def is_likely_competitor(lead, service):
    """Exclude only a clearly evidenced direct competitor for the chosen offer.

    A name, website, or broad industry alone is not enough to classify a lead as
    a competitor. This intentionally avoids hard-coded assumptions about web
    agencies or any one seller's service catalogue.
    """
    offer_text = " ".join(str(lead.get(key) or "") for key in (
        "services_offered", "service_description", "evidence_text", "industry"
    )).lower()
    service_text = (service or "").strip().lower()
    if not offer_text or not service_text:
        return False
    service_tokens = [token for token in re.findall(r"[a-z0-9]+", service_text) if len(token) > 3]
    if not service_tokens:
        return False
    overlap = sum(1 for token in set(service_tokens) if token in offer_text)
    return overlap >= max(1, min(2, len(set(service_tokens))))



def find_public_business_email(website_url):
    """Find an email explicitly published on a business homepage.

    This deliberately checks only one page with a short timeout so a Google
    Places search cannot block for several seconds per lead. It does not verify
    ownership or guarantee delivery.
    """
    if not website_url:
        return ""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(website_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return ""
        headers = {"User-Agent": "AltairBusinessSuiteLeadResearch/1.0"}
        try:
            response = requests.get(
                website_url,
                headers=headers,
                timeout=(0.8, 1.2),
                allow_redirects=True,
                stream=True
            )
            try:
                if response.status_code >= 400:
                    return ""
                # Read a small, bounded amount of homepage HTML only.
                chunks = []
                total = 0
                for chunk in response.iter_content(chunk_size=16384, decode_unicode=True):
                    if not chunk:
                        continue
                    if isinstance(chunk, bytes):
                        chunk = chunk.decode("utf-8", errors="ignore")
                    remaining = 150000 - total
                    if remaining <= 0:
                        break
                    chunk = chunk[:remaining]
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= 150000:
                        break
                html = "".join(chunks)
                for address in re.findall(
                    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
                    html,
                    flags=re.IGNORECASE
                ):
                    address = address.strip(".,;:()[]{}<>").lower()
                    if not address.endswith((".png", ".jpg", ".jpeg", ".webp", ".svg", ".css", ".js")):
                        return address
            finally:
                response.close()
        except requests.RequestException:
            return ""
        return ""
    except Exception as exc:
        print("PUBLIC EMAIL LOOKUP ERROR:", type(exc).__name__)
        return ""


def _lead_text_requests_service(text, service):
    'Classify actual source text; optionally use a configured Qwen-compatible endpoint.'
    raw_text = (text or "").strip()
    service = (service or "").strip()
    if not raw_text or not service:
        return 0, ""
    qwen_url = os.environ.get("QWEN_API_URL", "").strip()
    qwen_key = os.environ.get("QWEN_API_KEY", "").strip()
    qwen_model = os.environ.get("QWEN_MODEL", "qwen-plus").strip()
    if qwen_url and qwen_key:
        try:
            llm_response = requests.post(
                qwen_url,
                headers={"Authorization": f"Bearer {qwen_key}", "Content-Type": "application/json"},
                json={
                    "model": qwen_model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": "Classify only the supplied text. Do not infer facts. Return JSON only with intent equal to explicit_request, vague_interest, or none, and a short evidence quote copied from the text."},
                        {"role": "user", "content": f"Service offered: {service}\nSource text: {raw_text[:4000]}\nDoes the text clearly show that the author wants to buy or hire for this service?"}
                    ]
                },
                timeout=8
            )
            llm_response.raise_for_status()
            content = llm_response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content[content.find("{"):content.rfind("}") + 1])
            intent = str(parsed.get("intent", "none")).lower()
            quote = str(parsed.get("evidence", "")).strip()
            if quote and quote.lower() in raw_text.lower():
                if intent == "explicit_request":
                    return 25, "Configured Qwen classifier found an explicit request in source text: " + quote
                if intent == "vague_interest":
                    return 10, "Configured Qwen classifier found vague interest in source text: " + quote
            return 0, ""
        except Exception as exc:
            print("QWEN LEAD INTENT CLASSIFICATION ERROR:", exc)
            # Continue with the conservative local text classifier.

    text = raw_text.lower()
    service = service.lower()
    website_service = any(term in service for term in (
        "website", "web development", "web design", "e-commerce", "ecommerce", "online store"
    ))
    if website_service:
        explicit_patterns = [
            r"\bi need (a |an )?(website|web site|online store|e-?commerce site)\b",
            r"\blooking for (a |an )?(website developer|web developer|someone to build|web designer)\b",
            r"\bcan anyone recommend (a |an )?(website|web|web developer|website developer)\b",
            r"\bwho can help me (build|create|develop)\b.{0,50}\b(website|web site|online store)\b",
            r"\bneed someone to (build|create|design|develop)\b.{0,50}\b(website|web site|online store)\b",
            r"\bseeking (a |an )?(web developer|website developer|web designer)\b"
        ]
        vague_patterns = [
            r"\bthinking about (getting|building|creating) (a )?(website|online store)\b",
            r"\binterested in (a )?(website|online store|web design)\b",
            r"\bwebsite (ideas|recommendations|suggestions)\b"
        ]
    else:
        words = [w for w in re.findall(r"[a-z0-9]+", service) if len(w) > 2]
        if not words or not any(word in text for word in words):
            return 0, ""
        first = re.escape(words[0])
        explicit_patterns = [
            r"\bi need\b.{0,80}\b" + first + r"\b",
            r"\blooking to hire\b.{0,80}\b" + first + r"\b",
            r"\brecommend\b.{0,80}\b" + first + r"\b"
        ]
        vague_patterns = [r"\binterested in\b.{0,80}\b" + first + r"\b"]
    if any(re.search(p, text, re.I) for p in explicit_patterns):
        return 25, "Available source text contains an explicit request matching the selected service."
    if any(re.search(p, text, re.I) for p in vague_patterns):
        return 10, "Available source text shows vague interest in the selected service."
    return 0, ""


def qualify_lead_with_ai(lead, service, target_industry, target_location, business_size, keywords, user_id=None, sender_name="our team"):
    """Evidence-based, seller-neutral lead score (0-100).

    Main score: missing public service/product details (40), buying intent (25),
    recency (10), relevance (5). Supplementary evidence is capped at 20.
    Missing website is NOT a scoring criterion.
    """
    from datetime import datetime
    prospect_name = (lead.get("company_name") or "").strip()
    website = (lead.get("website") or "").strip()
    email = (lead.get("email") or "").strip()
    phone = (lead.get("phone") or "").strip()
    industry = (lead.get("industry") or "").strip()
    address = (lead.get("address") or lead.get("location") or "").strip()
    business_status = (lead.get("business_status") or "").upper()
    source_url = (lead.get("source_url") or lead.get("google_maps_url") or "").strip()
    source_text = (lead.get("evidence_text") or lead.get("post_text") or lead.get("source_text") or "").strip()
    published_at = lead.get("published_at") or lead.get("post_published_at") or lead.get("listing_date")
    reasons, analysis_points = [], []

    # A. Missing service/product information: a flexible opportunity signal.
    # The existence of a website alone does not prove that offerings are listed.
    service_listing = (lead.get("services_offered") or lead.get("service_description") or lead.get("offering_evidence") or "").strip()
    if not service_listing and not source_text:
        missing_service_info_points = 40
        reasons.append("The available public listing does not show a clear list or description of services/products; this is an information gap, not proof that the prospect offers none.")
        analysis_points.append("No clear services/products list was supplied by the source, so the information-gap signal earned 40 points. Website presence or absence was not used for this score.")
    elif not service_listing and source_text and not re.search(r"\b(service|services|product|products|offering|offers|speciali[sz]e|provide|provides|we do|menu|treatments|solutions)\b", source_text, re.I):
        missing_service_info_points = 40
        reasons.append("The available public text does not clearly describe services/products.")
        analysis_points.append("The public snippet does not clearly describe services/products; the website field itself does not affect this score.")
    else:
        missing_service_info_points = 0
        analysis_points.append("Public text includes service/product information, so no missing-offerings points were awarded.")

    # B. Buying intent: only source text with actual evidence can earn points.
    intent_points, intent_reason = _lead_text_requests_service(source_text, service)
    if intent_reason:
        reasons.append(intent_reason)
    else:
        analysis_points.append("No source text demonstrating a request to buy the selected service was available; buying-intent points are zero.")

    # C. Recency: only use a source-provided timestamp.
    recency_points = 0
    if published_at:
        try:
            published_dt = published_at if isinstance(published_at, datetime) else datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
            now = datetime.now(published_dt.tzinfo) if published_dt.tzinfo else datetime.now()
            age_hours = max(0, (now - published_dt).total_seconds() / 3600)
            if age_hours < 2: recency_points = 10
            elif age_hours < 6: recency_points = 7
            elif age_hours < 24: recency_points = 4
            elif age_hours <= 72: recency_points = 2
        except (ValueError, TypeError, OverflowError):
            analysis_points.append("The source timestamp could not be parsed; no recency points were awarded.")
    else:
        analysis_points.append("No original publication timestamp was available; no recency points were awarded.")

    # D. Relevance is derived dynamically from the user's chosen search terms.
    relevance_points = 0
    service_tokens = [w for w in re.findall(r"[a-z0-9]+", (service or "").lower()) if len(w) > 3]
    target_tokens = [w for w in re.findall(r"[a-z0-9]+", " ".join([target_industry or "", keywords or ""]).lower()) if len(w) > 3]
    searchable_text = " ".join([industry, source_text, " ".join(lead.get("types") or [])]).lower()
    if any(token in searchable_text for token in service_tokens + target_tokens):
        relevance_points = 5
        analysis_points.append("Available listing text/category matches one or more of the selected service, industry, or keyword terms.")
    else:
        analysis_points.append("No direct text/category match was available for the selected search terms; no relevance points were awarded.")

    main_score = min(80, missing_service_info_points + intent_points + recency_points + relevance_points)

    # Supplementary evidence: each supported criterion earns one point, capped at 20.
    supplementary = 0
    supplementary_reasons = []
    def award(condition, label):
        nonlocal supplementary
        if condition and supplementary < 20:
            supplementary += 1
            supplementary_reasons.append(label)

    award(bool(phone), "A public phone number is listed.")
    award(bool(email and lead.get("email_verified") is True), "Email is verified by a reliable process.")
    award(bool(address), "A location/address is available from the source.")
    target_location_l = (target_location or "").lower()
    award(bool(target_location_l and address and target_location_l in address.lower()), "Location matches the requested location text.")
    award(bool(prospect_name and prospect_name.lower() not in ("unknown business", "unknown", "public profile / request")), "A prospect/profile name is available.")
    award(bool(industry and (not target_industry or target_industry.lower() in industry.lower() or industry.lower() in target_industry.lower())), "Category is consistent with the selected target industry.")
    award(business_status == "OPERATIONAL", "The business listing is marked operational.")
    award(bool(source_url), "A public source/profile URL is available.")
    award(bool(lead.get("social_url")), "A public social profile URL is available.")
    award(bool(phone or email or website), "At least one public contact channel is listed.")
    award(bool(published_at), "The original source date is recorded.")
    award(bool(website or source_url), "A public online profile or source page is available.")
    award(bool(lead.get("visibility_issue_evidence")), "Evidence supports an online-visibility opportunity.")
    award(bool(lead.get("mobile_friendly_evidence")), "Evidence supports a mobile usability opportunity.")
    award(bool(lead.get("booking_feature_evidence")), "Evidence supports a booking opportunity.")
    award(bool(lead.get("ecommerce_feature_evidence")), "Evidence supports an e-commerce opportunity.")
    award(bool(lead.get("contact_form_evidence")), "Evidence supports an enquiry/contact opportunity.")
    award(bool(prospect_name and (phone or email or website or source_url)), "The prospect has a name and at least one supporting contact/source field.")

    if "_not_contacted_or_converted" in lead:
        not_contacted_or_converted = bool(lead.get("_not_contacted_or_converted"))
    else:
        not_contacted_or_converted = False
        if user_id and lead.get("google_place_id"):
            db = cursor = None
            try:
                db = get_db_connection()
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT lead_status FROM leads WHERE user_id=%s AND google_place_id=%s LIMIT 1", (user_id, lead.get("google_place_id")))
                existing = cursor.fetchone()
                not_contacted_or_converted = bool(not existing or (existing.get("lead_status") or "").lower() not in ("contacted", "converted"))
            except Exception as exc:
                print("LEAD STATUS SCORE CHECK ERROR:", type(exc).__name__, str(exc))
            finally:
                if cursor: cursor.close()
                if db: db.close()
    award(not_contacted_or_converted, "Lead is not recorded as contacted or converted in this user's database.")

    supplementary = min(20, supplementary)
    score = max(0, min(100, main_score + supplementary))
    quality = ("Excellent potential lead" if score >= 80 else "Strong potential lead" if score >= 60 else "Potential lead" if score >= 40 else "Weak potential lead" if score >= 20 else "Low potential lead")
    analysis_points.append(f"Score breakdown: missing service/product information {missing_service_info_points}%, buying intent {intent_points}%, recency {recency_points}%, relevance {relevance_points}%, supplementary evidence {supplementary}%. Final lead score: {score}%.")
    ai_analysis = f"{prospect_name or 'This prospect'} was evaluated for {service or 'the selected offer'}. " + " ".join(analysis_points)
    ai_reason = " ".join(reasons) if reasons else "Score is based only on available source evidence. Verify details before outreach."
    sender_name = (sender_name or "our team").strip() or "our team"
    recipient_greeting = prospect_name or "there"
    ai_message = (
        f"Hi {recipient_greeting},\n\n"
        f"I came across your public profile/listing while researching potential contacts in {target_location or 'your area'}.\n\n"
        f"I’m reaching out from {sender_name}. We offer {service or 'services relevant to your needs'} and I wanted to ask whether this is something you may be interested in discussing.\n\n"
        "If this is not relevant, no problem at all.\n\n"
        f"Kind regards,\n{sender_name}"
    )
    return {"lead_score": score, "ai_analysis": ai_analysis, "ai_reason": ai_reason,
            "ai_message": ai_message, "lead_quality": quality,
            "score_breakdown": {"missing_service_information": missing_service_info_points, "buying_intent": intent_points,
                                "recency": recency_points, "service_relevance": relevance_points,
                                "main_score": main_score, "supplementary_score": supplementary,
                                "final_score": score, "supplementary_reasons": supplementary_reasons}}


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
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    google_place_id = request.form.get("google_place_id", "").strip()
    try:
        lead_score = max(0, min(100, int(request.form.get("lead_score", "0") or 0)))
    except (TypeError, ValueError):
        lead_score = 0
    ai_analysis = request.form.get("ai_analysis", "").strip()
    ai_reason = request.form.get("ai_reason", "").strip()
    ai_message = request.form.get("ai_message", "").strip()

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
            SELECT id, email
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
            # Enrich older saved records if the search has now found an email or website.
            cursor.execute("""
                UPDATE leads
                SET
                    email = CASE WHEN (email IS NULL OR email = '') AND %s <> '' THEN %s ELSE email END,
                    website = CASE WHEN (website IS NULL OR website = '') AND %s <> '' THEN %s ELSE website END,
                    phone = CASE WHEN (phone IS NULL OR phone = '') AND %s <> '' THEN %s ELSE phone END,
                    lead_score = GREATEST(COALESCE(lead_score, 0), %s)
                WHERE id = %s AND user_id = %s
            """, (email, email, website, website, phone, phone, lead_score, existing["id"], user_id))
            db.commit()
            cursor.close()
            db.close()
            return jsonify({
                "success": True,
                "already_saved": True,
                "lead_id": existing["id"],
                "message": "Lead was already saved; missing contact details were updated where available."
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
                email,
                phone,
                source,
                lead_status,
                lead_score,
                ai_analysis,
                ai_reason,
                ai_message,
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
                %s,
                'Google',
                'New',
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
            location,
            website,
            email,
            phone,
            lead_score,
            ai_analysis,
            ai_reason,
            ai_message,
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
                "email": email,
                "phone": phone,
                "website": website,
                "lead_status": "New",
                "lead_score": lead_score
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
