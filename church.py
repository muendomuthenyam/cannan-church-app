import hashlib
import os
import random
import re
import smtplib
import sqlite3
from datetime import datetime
from email.mime.text import MIMEText
import pandas as pd
import streamlit as st

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="CANAAN THE PLACE OF GOD CHURCH",
    page_icon="⛪",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================
# SECURE CONFIGURATION & SECRETS HELPER
# ==========================================
def get_secret(key: str, default=None):
  """Safely retrieves a secret from Streamlit secrets or environment variables without throwing StreamlitSecretNotFoundError."""
  try:
    if key in st.secrets:
      return st.secrets[key]
  except Exception:
    pass
  return os.environ.get(key, default)


# ==========================================
# DATABASE ENGINE & INITIALIZATION
# ==========================================
DB_FILE = "canaan_church.db"


def get_db_connection():
  conn = sqlite3.connect(DB_FILE, check_same_thread=False)
  conn.row_factory = sqlite3.Row
  return conn


def run_query(sql: str, params=()):
  """Executes a SELECT query and ensures connection is strictly closed."""
  conn = get_db_connection()
  try:
    return pd.read_sql_query(sql, conn, params=params)
  finally:
    conn.close()


def run_action(sql: str, params=()) -> bool:
  """Executes INSERT/UPDATE/DELETE action safely catching SQLite errors."""
  conn = get_db_connection()
  try:
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()
    return True
  except sqlite3.IntegrityError as e:
    st.error(f"⚠️ Unique Constraint Notice: {e}")
    return False
  except sqlite3.Error as e:
    st.error(f"⚠️ Database Error: {e}")
    return False
  finally:
    conn.close()


def init_db():
  conn = get_db_connection()
  try:
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                verified TEXT DEFAULT 'Yes',
                approval_status TEXT DEFAULT 'Pending Approval'
            )
        """)

    # Attendance Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                service_name TEXT NOT NULL,
                attendees INTEGER NOT NULL,
                notes TEXT
            )
        """)

    # Members Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                fellowship_group TEXT,
                department TEXT,
                household TEXT,
                join_date TEXT
            )
        """)

    # Finance Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS finance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                recorded_by TEXT NOT NULL,
                description TEXT
            )
        """)

    # M-Pesa Ledger Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS mpesa_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_no TEXT UNIQUE NOT NULL,
                sender_name TEXT NOT NULL,
                phone TEXT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

    # Theology & Discipleship Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS theology (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                course_unit TEXT NOT NULL,
                assignment_score REAL,
                exam_score REAL,
                status TEXT
            )
        """)

    # Facilities Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS facilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_name TEXT NOT NULL,
                booked_by TEXT NOT NULL,
                date TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                purpose TEXT
            )
        """)

    # SMS Broadcast Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS sms_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                target_audience TEXT NOT NULL,
                message_body TEXT NOT NULL,
                sent_by TEXT NOT NULL,
                status TEXT
            )
        """)

    # Counseling & Prayer Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS counseling_prayer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                submitted_by TEXT NOT NULL,
                request_type TEXT NOT NULL,
                details TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)

    # Visitor Pipeline Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS visitor_pipeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_name TEXT NOT NULL,
                phone TEXT,
                first_visit_date TEXT NOT NULL,
                assigned_leader TEXT,
                integration_status TEXT NOT NULL
            )
        """)

    # Church Assets Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS church_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_name TEXT NOT NULL,
                serial_number TEXT,
                condition TEXT NOT NULL,
                custodian TEXT NOT NULL,
                purchase_value REAL NOT NULL
            )
        """)

    # Announcements Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                message TEXT NOT NULL
            )
        """)

    # System Audit Trail Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user TEXT NOT NULL,
                action TEXT NOT NULL,
                module TEXT NOT NULL
            )
        """)

    # Live Stream Configuration Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS livestream_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stream_title TEXT NOT NULL,
                stream_url TEXT NOT NULL,
                is_live INTEGER DEFAULT 1,
                updated_by TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

    # Past Activities & Media Archive Table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS past_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                speaker TEXT NOT NULL,
                video_url TEXT NOT NULL,
                description TEXT,
                sermon_notes TEXT
            )
        """)

    # Populate initial default data if empty
    cursor.execute("SELECT COUNT(*) FROM announcements")
    if cursor.fetchone()[0] == 0:
      cursor.execute(
          "INSERT INTO announcements (sender, timestamp, message) VALUES (?,"
          " ?, ?)",
          (
              "Senior Pastor",
              "2026-09-28 06:00",
              (
                  "Praise God church! Welcome to Canaan Management"
                  " System."
              ),
          ),
      )

    cursor.execute("SELECT COUNT(*) FROM livestream_config")
    if cursor.fetchone()[0] == 0:
      cursor.execute(
          "INSERT INTO livestream_config (stream_title, stream_url, is_live,"
          " updated_by, updated_at) VALUES (?, ?, ?, ?, ?)",
          (
              "Sunday Main Worship & Word Service",
              "https://www.youtube.com/watch?v=5qap5aO4i9A",
              1,
              "Media Ministry",
              "2026-09-28 10:00",
          ),
      )

    cursor.execute("SELECT COUNT(*) FROM past_activities")
    if cursor.fetchone()[0] == 0:
      cursor.execute(
          "INSERT INTO past_activities (title, category, date, speaker,"
          " video_url, description, sermon_notes) VALUES (?, ?, ?, ?, ?, ?,"
          " ?)",
          (
              "Walking in Unshakable Faith",
              "Sunday Sermons",
              "2026-09-20",
              "Senior Pastor",
              "https://www.youtube.com/watch?v=5qap5aO4i9A",
              (
                  "A powerful teaching on building unwavering faith during"
                  " seasons of testing."
              ),
              "Key Scripture: Hebrews 11:1, Romans 10:17",
          ),
      )
      cursor.execute(
          "INSERT INTO past_activities (title, category, date, speaker,"
          " video_url, description, sermon_notes) VALUES (?, ?, ?, ?, ?, ?,"
          " ?)",
          (
              "Monthly Breakthrough Kesha",
              "Kesha & Night Services",
              "2026-08-28",
              "Guest Evangelist",
              "https://www.youtube.com/watch?v=5qap5aO4i9A",
              (
                  "Overnight prayer and deliverance service with praise and"
                  " worship."
              ),
              "Theme: The Power of Persistent Intercession",
          ),
      )

    conn.commit()
  finally:
    conn.close()


init_db()

# ==========================================
# SECURITY HELPERS & UTILITIES
# ==========================================
SALT = "canaan_church_secure_salt_2026"


def hash_password(password: str) -> str:
  return hashlib.sha256((password + SALT).encode("utf-8")).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
  return hash_password(password) == hashed_password


def log_audit(user: str, action: str, module: str):
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  run_action(
      "INSERT INTO audit_trail (timestamp, user, action, module) VALUES (?,"
      " ?, ?, ?)",
      (timestamp, user, action, module),
  )


def check_reverend_exists() -> bool:
  df = run_query(
      "SELECT COUNT(*) as cnt FROM users WHERE role IN ('Reverend', 'Senior"
      " Pastor / Overseer')"
  )
  return int(df.iloc[0]["cnt"]) > 0 if not df.empty else False


def format_youtube_url(url: str) -> str:
  if not url:
    return ""
  youtube_regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
  match = re.search(youtube_regex, url)
  if match:
    video_id = match.group(1)
    return f"https://www.youtube.com/watch?v={video_id}"
  return url


# ==========================================
# SMTP / EMAIL ENGINE
# ==========================================
def dispatch_otp_email(recipient_email: str, otp_code: str) -> bool:
  smtp_server = get_secret("SMTP_SERVER", "smtp.gmail.com")
  port_raw = get_secret("SMTP_PORT", 587)
  try:
    smtp_port = int(port_raw)
  except (ValueError, TypeError):
    smtp_port = 587

  sender_email = get_secret("SMTP_EMAIL", "muendomuthenyam@gmail.com")
  sender_password = get_secret("SMTP_PASSWORD", "raar eeib vfff pgdc")

  if sender_email and sender_password:
    try:
      msg = MIMEText(
          f"Shalom!\n\nYour Canaan Church Verification Code is:"
          f" {otp_code}\n\nThis code will expire in 10 minutes.\n\nBlessings,\nCanaan"
          " Management System"
      )
      msg["Subject"] = "Canaan Church - Portal Verification Code"
      msg["From"] = f"Canaan Church Portal <{sender_email}>"
      msg["To"] = recipient_email

      server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
      server.starttls()
      server.login(sender_email, sender_password)
      server.sendmail(sender_email, recipient_email, msg.as_string())
      server.quit()
      return True
    except Exception as e:
      st.error(
          "SMTP Gateway Warning: Could not dispatch live email"
          f" ({e}). Using simulated verification mode."
      )
      return False
  return False


# ==========================================
# STYLING & MODERN THEMING
# ==========================================
st.markdown(
    """
    <style>
    .main { 
        background-color: #f8fafc; 
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    .hero-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
        padding: 32px 25px;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
        border-bottom: 5px solid #d4af37;
    }
    .hero-box h1 {
        font-size: 2.5rem;
        margin-bottom: 8px;
        font-weight: 800;
        letter-spacing: 0.5px;
        color: #ffffff;
    }
    .verse-text {
        font-style: italic;
        font-size: 1.1rem;
        color: #f1f5f9;
        margin-top: 6px;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 20px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        border-left: 5px solid #2563eb;
        margin-bottom: 15px;
        transition: transform 0.2s ease;
    }
    .metric-card h3 {
        color: #64748b;
        font-size: 0.95rem;
        margin: 0 0 6px 0;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-card h2 {
        color: #0f172a;
        font-size: 1.8rem;
        margin: 0;
        font-weight: 700;
    }
    .whatsapp-chat-box {
        background-color: #f1f5f9;
        padding: 20px;
        border-radius: 12px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
        max-height: 520px;
        overflow-y: auto;
    }
    .chat-bubble {
        background-color: #ffffff;
        padding: 14px 18px;
        border-radius: 10px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border-left: 4px solid #10b981;
    }
    .chat-sender {
        font-weight: 700;
        color: #047857;
        font-size: 0.95rem;
    }
    .chat-time {
        font-size: 0.78rem;
        color: #94a3b8;
        float: right;
    }
    .chat-msg {
        margin-top: 6px;
        color: #1e293b;
        font-size: 1rem;
        line-height: 1.5;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "authenticated" not in st.session_state:
  st.session_state["authenticated"] = False
if "reset_step" not in st.session_state:
  st.session_state["reset_step"] = 1
if "reg_step" not in st.session_state:
  st.session_state["reg_step"] = 1

# ==========================================
# UNIVERSAL AUTHENTICATION GATE
# ==========================================
if not st.session_state["authenticated"]:
  st.markdown(
      """
        <div class="hero-box">
            <h1>⛪ CANAAN THE PLACE OF GOD CHURCH</h1>
            <p class="verse-text">"God is spirit, and his worshipers must worship in the spirit and in truth." — <b>John 4:24</b></p>
        </div>
    """,
      unsafe_allow_html=True,
  )

  tab_login, tab_register, tab_forgot = st.tabs([
      "🔐 Secure Login",
      "📝 New Account Registration",
      "🔑 Forgot Password?",
  ])

  with tab_login:
    st.subheader("Login to Community Portal")
    with st.form("login_form"):
      login_email = st.text_input("Email Address")
      login_password = st.text_input("Password", type="password")
      submit_login = st.form_submit_button("Sign In", use_container_width=True)

      if submit_login:
        user_df = run_query(
            "SELECT * FROM users WHERE email = ?", (login_email.strip(),)
        )
        if not user_df.empty:
          user_record = user_df.iloc[0]
          if verify_password(login_password, user_record["password_hash"]):
            approval_status = user_record["approval_status"]
            if approval_status == "Pending Approval":
              st.warning(
                  "⚠️ Your account is registered and verified, but it is"
                  " currently pending approval by the Reverend."
              )
            elif approval_status == "Rejected":
              st.error(
                  "❌ Your account registration was rejected by"
                  " administration."
              )
            else:
              st.session_state["authenticated"] = True
              st.session_state["user_role"] = user_record["role"]
              st.session_state["current_user"] = user_record["full_name"]
              st.session_state["user_email"] = user_record["email"]
              log_audit(
                  user_record["full_name"],
                  f"Logged in successfully as {user_record['role']}",
                  "Security",
              )
              st.success("Login successful! Entering portal...")
              st.rerun()
          else:
            st.error("Invalid email address or password.")
        else:
          st.error("Invalid email address or password.")

  with tab_register:
    st.subheader("Register New Account with Email Verification")

    reverend_already_exists = check_reverend_exists()

    if reverend_already_exists:
      st.info(
          "🔒 **System Security Notice:** The primary Reverend account for"
          " Canaan Church is already registered. Standard registration is open"
          " for church members and leadership staff."
      )

    if st.session_state["reg_step"] == 1:
      with st.form("reg_form_1"):
        reg_name = st.text_input("Full Name")
        reg_email = st.text_input("Email Address")
        reg_phone = st.text_input("Phone Number (e.g., +254712345678)")
        reg_pass = st.text_input("Create Password", type="password")
        reg_pass_conf = st.text_input("Confirm Password", type="password")

        all_roles = [
            "General Church Member",
            "Ushers",
            "Chief Chef",
            "Chair-Man/Lady",
            "Fellowship & Ministry Leader",
            "Pastor",
            "Reverend",
            "Church Treasurer",
            "Senior Pastor / Overseer",
        ]

        if reverend_already_exists:
          allowed_roles = [
              r
              for r in all_roles
              if r not in ["Reverend", "Senior Pastor / Overseer"]
          ]
        else:
          allowed_roles = all_roles

        reg_role = st.selectbox("Select Role", allowed_roles)
        next_btn = st.form_submit_button(
            "Send Verification Code", use_container_width=True
        )

        if next_btn:
          if not reg_email or not reg_name or not reg_pass:
            st.warning("Please fill in all required fields.")
          elif reg_pass != reg_pass_conf:
            st.error("Passwords do not match.")
          elif (
              reg_role in ["Reverend", "Senior Pastor / Overseer"]
              and reverend_already_exists
          ):
            st.error(
                "⛔ Security Restriction: A Reverend account already exists in"
                " this system. Only one Reverend account is permitted."
            )
          else:
            existing = run_query(
                "SELECT id FROM users WHERE email = ?", (reg_email.strip(),)
            )
            if not existing.empty:
              st.error("An account with this email address already exists.")
            else:
              otp = random.randint(100000, 999999)
              st.session_state["reg_otp"] = str(otp)
              st.session_state["temp_reg"] = {
                  "Full Name": reg_name,
                  "Email": reg_email.strip(),
                  "Phone": reg_phone.strip(),
                  "Password": reg_pass,
                  "Role": reg_role,
              }

              dispatched = dispatch_otp_email(reg_email.strip(), str(otp))
              st.session_state["otp_sent_via_smtp"] = dispatched

              st.session_state["reg_step"] = 2
              st.rerun()

    elif st.session_state["reg_step"] == 2:
      temp_reg = st.session_state.get("temp_reg", {})
      target_email = temp_reg.get("Email", "")
      st.info(f"A verification code has been dispatched to **{target_email}**.")

      if not st.session_state.get("otp_sent_via_smtp", False):
        st.warning(
            "🔒 [SIMULATED EMAIL SYSTEM] Your Verification Code is:"
            f" **{st.session_state.get('reg_otp', '')}**"
        )
      else:
        st.success("✉️ Verification email sent via SMTP server.")

      with st.form("reg_form_2"):
        entered_otp = st.text_input("Enter 6-Digit Verification Code")
        verify_btn = st.form_submit_button(
            "Verify & Complete Registration", use_container_width=True
        )

        if verify_btn:
          if entered_otp.strip() == st.session_state.get("reg_otp", ""):
            new_u = st.session_state.get("temp_reg", {})
            if new_u:
              approval_status = (
                  "Approved"
                  if new_u.get("Role")
                  in ["Reverend", "Senior Pastor / Overseer"]
                  else "Pending Approval"
              )
              hashed_p = hash_password(new_u.get("Password", ""))

              success = run_action(
                  "INSERT INTO users (full_name, email, phone, password_hash,"
                  " role, verified, approval_status) VALUES (?, ?, ?, ?, ?,"
                  " 'Yes', ?)",
                  (
                      new_u.get("Full Name"),
                      new_u.get("Email"),
                      new_u.get("Phone"),
                      hashed_p,
                      new_u.get("Role"),
                      approval_status,
                  ),
              )

              if success:
                if (
                    approval_status == "Approved"
                    or new_u.get("Role") == "General Church Member"
                ):
                  today_str = datetime.today().strftime("%Y-%m-%d")
                  run_action(
                      "INSERT INTO members (full_name, phone, email,"
                      " fellowship_group, department, household, join_date)"
                      " VALUES (?, ?, ?, 'Canaan Men', ?, 'Independent', ?)",
                      (
                          new_u.get("Full Name"),
                          new_u.get("Phone") if new_u.get("Phone") else "N/A",
                          new_u.get("Email"),
                          new_u.get("Role"),
                          today_str,
                      ),
                  )

                log_audit(
                    new_u.get("Full Name"),
                    f"Registered new account as {new_u.get('Role')} (Status:"
                    f" {approval_status})",
                    "Security",
                )
                st.success(
                    "Account verified successfully! Your profile is now"
                    " registered."
                )
                st.session_state["reg_step"] = 1
                st.rerun()
          else:
            st.error("Invalid verification code.")

  with tab_forgot:
    st.subheader("Reset Password via Email Verification")
    if st.session_state["reset_step"] == 1:
      with st.form("forgot_form_1"):
        reset_email = st.text_input("Enter Your Registered Email")
        send_reset_btn = st.form_submit_button(
            "Send Password Reset Code", use_container_width=True
        )

        if send_reset_btn:
          existing = run_query(
              "SELECT id FROM users WHERE email = ?", (reset_email.strip(),)
          )
          if not existing.empty:
            otp_reset = random.randint(100000, 999999)
            st.session_state["reset_otp"] = str(otp_reset)
            st.session_state["reset_email"] = reset_email.strip()

            dispatched = dispatch_otp_email(
                reset_email.strip(), str(otp_reset)
            )
            st.session_state["reset_otp_sent_via_smtp"] = dispatched

            st.session_state["reset_step"] = 2
            st.rerun()
          else:
            st.error("Email address not found in system records.")

    elif st.session_state["reset_step"] == 2:
      res_email = st.session_state.get("reset_email", "")
      st.info(f"Password reset code sent to **{res_email}**.")
      if not st.session_state.get("reset_otp_sent_via_smtp", False):
        st.warning(
            "🔒 [SIMULATED EMAIL SYSTEM] Your Reset Code is:"
            f" **{st.session_state.get('reset_otp', '')}**"
        )

      with st.form("forgot_form_2"):
        entered_reset_otp = st.text_input("Enter 6-Digit Reset Code")
        new_password = st.text_input("Enter New Password", type="password")
        confirm_new_password = st.text_input(
            "Confirm New Password", type="password"
        )

        reset_submit = st.form_submit_button(
            "Reset Password", use_container_width=True
        )
        if reset_submit:
          if entered_reset_otp.strip() == st.session_state.get(
              "reset_otp", ""
          ):
            if new_password != confirm_new_password:
              st.error("Passwords do not match.")
            else:
              email_target = st.session_state.get("reset_email", "")
              hashed_p = hash_password(new_password)
              run_action(
                  "UPDATE users SET password_hash = ? WHERE email = ?",
                  (hashed_p, email_target),
              )
              log_audit(email_target, "Reset password successfully", "Security")
              st.success(
                  "Password successfully reset! Please proceed to login."
              )
              st.session_state["reset_step"] = 1
              st.rerun()
          else:
            st.error("Invalid reset code.")
  st.stop()

# ==========================================
# MAIN APPLICATION HEADER
# ==========================================
st.markdown(
    """
    <div class="hero-box">
        <h1>⛪ CANAAN THE PLACE OF GOD CHURCH</h1>
        <p class="verse-text">"God is spirit, and his worshipers must worship in the spirit and in truth." — <b>John 4:24</b></p>
    </div>
""",
    unsafe_allow_html=True,
)

current_user = st.session_state.get("current_user", "Member")
current_role = st.session_state.get("user_role", "Member")

# ==========================================
# SIDEBAR NAVIGATION & STRICT RBAC ROUTER
# ==========================================
st.sidebar.title("Navigation Hub")
st.sidebar.markdown(f"👤 User: **{current_user}**")
st.sidebar.markdown(f"🔑 Role: **{current_role}**")
st.sidebar.markdown("---")

if st.sidebar.button("Lock System (Logout)", use_container_width=True):
  log_audit(current_user, "Logged out of the system", "Security")
  st.session_state["authenticated"] = False
  st.rerun()

st.sidebar.markdown("---")

# Define Modules by Role Hierarchy
if current_role in ["Reverend", "Senior Pastor / Overseer"]:
  nav_options = [
      "📊 Dashboard Overview",
      "📺 Live Streaming & Media Archive",
      "👑 Reverend Member Approval Desk",
      "💬 WhatsApp Announcement Board",
      "📱 SMS & WhatsApp Reminders",
      "🙏 Counseling & Prayer Tracker",
      "🚪 Visitor & New Convert Pipeline",
      "📦 Asset & Inventory Management",
      "🕒 Weekly Schedule Hub",
      "👥 Fellowships & Households",
      "📝 Attendance Tracker",
      "📁 Member Directory",
      "🎓 Theology & Discipleship",
      "📅 Facility Booking Hub",
      "💰 Tithes & Financial Analytics",
      "📲 M-Pesa Integration Ledger",
      "🛡️ System Audit Trail",
  ]
elif current_role == "Chair-Man/Lady":
  nav_options = [
      "📊 Dashboard Overview",
      "📺 Live Streaming & Media Archive",
      "💬 WhatsApp Announcement Board",
      "👥 Fellowships & Households",
      "📁 Member Directory",
      "🕒 Weekly Schedule Hub",
  ]
elif current_role == "Ushers":
  nav_options = [
      "📊 Dashboard Overview",
      "📺 Live Streaming & Media Archive",
      "📝 Attendance Tracker",
      "🚪 Visitor & New Convert Pipeline",
      "🕒 Weekly Schedule Hub",
      "💬 WhatsApp Announcement Board",
  ]
elif current_role == "Chief Chef":
  nav_options = [
      "📊 Dashboard Overview",
      "📺 Live Streaming & Media Archive",
      "📅 Facility Booking Hub",
      "📦 Asset & Inventory Management",
      "💬 WhatsApp Announcement Board",
  ]
elif current_role in ["Pastor", "Fellowship & Ministry Leader"]:
  nav_options = [
      "📊 Dashboard Overview",
      "📺 Live Streaming & Media Archive",
      "💬 WhatsApp Announcement Board",
      "📱 SMS & WhatsApp Reminders",
      "🙏 Counseling & Prayer Tracker",
      "🚪 Visitor & New Convert Pipeline",
      "🕒 Weekly Schedule Hub",
      "👥 Fellowships & Households",
      "📝 Attendance Tracker",
      "📁 Member Directory",
      "🎓 Theology & Discipleship",
      "📅 Facility Booking Hub",
  ]
elif current_role == "Church Treasurer":
  nav_options = [
      "📊 Dashboard Overview",
      "📺 Live Streaming & Media Archive",
      "💬 WhatsApp Announcement Board",
      "💰 Tithes & Financial Analytics",
      "📲 M-Pesa Integration Ledger",
      "📁 Member Directory",
      "📦 Asset & Inventory Management",
  ]
else:
  nav_options = [
      "📊 Dashboard Overview",
      "📺 Live Streaming & Media Archive",
      "💬 WhatsApp Announcement Board",
      "🙏 Counseling & Prayer Tracker",
      "🕒 Weekly Schedule Hub",
      "👥 Fellowships & Households",
      "🎓 Theology & Discipleship",
  ]

app_mode = st.sidebar.radio("Choose a Module:", nav_options)

if app_mode not in nav_options:
  st.error(
      "⛔ Access Denied: Your account role does not have permission to access"
      " this module."
  )
  st.stop()

# ==========================================
# 1. DASHBOARD OVERVIEW
# ==========================================
if app_mode == "📊 Dashboard Overview":
  st.subheader(f"Welcome back, {current_user}!")
  st.caption(
      "Real-time digital management portal for Canaan The Place of God Church."
  )

  col1, col2, col3, col4 = st.columns(4)
  with col1:
    m_df = run_query("SELECT COUNT(*) as total FROM members")
    m_cnt = m_df.iloc[0]["total"] if not m_df.empty else 0
    st.markdown(
        f"""
            <div class="metric-card">
                <h3>Total Members</h3>
                <h2>{m_cnt}</h2>
            </div>
        """,
        unsafe_allow_html=True,
    )
  with col2:
    v_df = run_query("SELECT COUNT(*) as total FROM visitor_pipeline")
    v_cnt = v_df.iloc[0]["total"] if not v_df.empty else 0
    st.markdown(
        f"""
            <div class="metric-card" style="border-left-color: #10b981;">
                <h3>New Visitors</h3>
                 baseline <h2>{v_cnt}</h2>
            </div>
        """,
        unsafe_allow_html=True,
    )
  with col3:
    p_df = run_query(
        "SELECT COUNT(*) as total FROM counseling_prayer WHERE status !="
        " 'Prayed For / Resolved'"
    )
    p_cnt = p_df.iloc[0]["total"] if not p_df.empty else 0
    st.markdown(
        f"""
            <div class="metric-card" style="border-left-color: #f59e0b;">
                <h3>Active Prayers</h3>
                <h2>{p_cnt}</h2>
            </div>
        """,
        unsafe_allow_html=True,
    )
  with col4:
    f_df = run_query("SELECT SUM(amount) as total FROM finance")
    f_total = (
        f_df.iloc[0]["total"] if not f_df.empty and f_df.iloc[0]["total"] else 0.0
    )
    display_funds = (
        f"KES {f_total:,.2f}"
        if current_role
        in ["Senior Pastor / Overseer", "Reverend", "Church Treasurer"]
        else "🔒 Restricted"
    )
    st.markdown(
        f"""
            <div class="metric-card" style="border-left-color: #8b5cf6;">
                <h3>Treasury Funds</h3>
                <h2>{display_funds}</h2>
            </div>
        """,
        unsafe_allow_html=True,
    )

  st.markdown("---")

  col_dash1, col_dash2 = st.columns([1, 1])
  with col_dash1:
    st.subheader("📢 Recent Announcements")
    recent_ann = run_query(
        "SELECT * FROM announcements ORDER BY id DESC LIMIT 3"
    )
    for _, r in recent_ann.iterrows():
      st.info(f"**{r['sender']}** ({r['timestamp']}):\n\n{r['message']}")

  with col_dash2:
    st.subheader("📅 Service Attendance Trend")
    att_summary = run_query(
        "SELECT date, service_name, attendees FROM attendance ORDER BY id DESC"
        " LIMIT 5"
    )
    if not att_summary.empty:
      st.dataframe(att_summary, use_container_width=True)
    else:
      st.caption("No recent attendance records logged yet.")

# ==========================================
# 2. LIVE STREAMING & MEDIA ARCHIVE
# ==========================================
elif app_mode == "📺 Live Streaming & Media Archive":
  st.subheader("📺 Online Streaming & Past Activities Hub")

  tab_live, tab_archive = st.tabs([
      "🔴 Live Stream Broadcast",
      "📚 Past Activities & Sermons Archive",
  ])

  with tab_live:
    live_info = run_query(
        "SELECT * FROM livestream_config ORDER BY id DESC LIMIT 1"
    )
    stream_title, stream_url, is_live = "Sunday Service", "", False
    if not live_info.empty:
      stream_data = live_info.iloc[0]
      is_live = bool(stream_data["is_live"])
      stream_title = stream_data["stream_title"]
      stream_url = format_youtube_url(stream_data["stream_url"])
      updated_at = stream_data["updated_at"]

      if is_live:
        st.markdown(
            "### 🔴 <span style='color:#ef4444;'>LIVE NOW</span> - "
            + stream_title,
            unsafe_allow_html=True,
        )
      else:
        st.markdown(
            "### ⏸️ <span style='color:#64748b;'>OFFLINE / UPCOMING"
            " SERVICE</span> - "
            + stream_title,
            unsafe_allow_html=True,
        )

      st.caption(f"Last updated: {updated_at} by {stream_data['updated_by']}")

      if stream_url:
        try:
          st.video(stream_url)
        except Exception:
          st.warning(
              "Unable to embed video directly. You can watch using this link:"
              f" [{stream_url}]({stream_url})"
          )

      col_pray, col_notes = st.columns(2)
      with col_pray:
        with st.form("live_prayer_form", clear_on_submit=True):
          st.write("🙏 **Send Live Prayer Request / Testimony**")
          p_name = st.text_input("Name", value=current_user)
          p_msg = st.text_area("Your Prayer Request")
          p_sub = st.form_submit_button(
              "Submit to Pastor", use_container_width=True
          )
          if p_sub:
            if p_msg.strip():
              today_str = datetime.today().strftime("%Y-%m-%d")
              run_action(
                  "INSERT INTO counseling_prayer (date, submitted_by,"
                  " request_type, details, status) VALUES (?, ?, 'Live Stream"
                  " Prayer Request', ?, 'Pending Pastor Review')",
                  (today_str, p_name, p_msg),
              )
              log_audit(
                  current_user,
                  "Submitted prayer request during Live Stream",
                  "Live Stream",
              )
              st.success("Prayer request sent to intercessory team!")
            else:
              st.warning("Please type your prayer request.")

      with col_notes:
        st.write("📝 **Service Notes & Giving**")
        st.info(
            "Welcome to our online service! Support ministry via M-Pesa Paybill"
            " or submit prayer requests in real time."
        )
        st.markdown(
            "**M-Pesa Tithes & Offerings:** Use the M-Pesa Ledger module to"
            " post receipts directly."
        )

    if current_role in [
        "Reverend",
        "Senior Pastor / Overseer",
        "Pastor",
        "Ushers",
        "Fellowship & Ministry Leader",
    ]:
      st.markdown("---")
      st.subheader("⚙️ Live Stream Control Panel (Media Team)")
      with st.form("update_stream_form"):
        new_title = st.text_input(
            "Stream Title / Event Name", value=stream_title
        )
        new_url = st.text_input(
            "Live Stream Video URL (YouTube / Video Link)",
            value=(
                stream_url
                if stream_url
                else "https://www.youtube.com/watch?v=5qap5aO4i9A"
            ),
        )
        live_status = st.checkbox(
            "Broadcast is Currently LIVE", value=is_live
        )
        update_btn = st.form_submit_button(
            "Update Live Stream Settings", use_container_width=True
        )

        if update_btn:
          ts_now = datetime.now().strftime("%Y-%m-%d %H:%M")
          is_live_int = 1 if live_status else 0
          run_action(
              "INSERT INTO livestream_config (stream_title, stream_url,"
              " is_live, updated_by, updated_at) VALUES (?, ?, ?, ?, ?)",
              (
                  new_title,
                  format_youtube_url(new_url),
                  is_live_int,
                  current_user,
                  ts_now,
              ),
          )
          log_audit(
              current_user,
              f"Updated Live Stream config: '{new_title}' (Live={is_live_int})",
              "Live Stream",
          )
          st.success("Live stream configuration updated successfully!")
          st.rerun()

  with tab_archive:
    st.markdown("### 📚 Past Services & Activity Archive")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
      search_term = st.text_input(
          "🔍 Search Activities by Title or Speaker", value=""
      )
    with col_f2:
      cat_filter = st.selectbox(
          "Filter by Category",
          [
              "All Categories",
              "Sunday Sermons",
              "Kesha & Night Services",
              "Midweek Fellowship",
              "Youth & Teens Events",
              "Special Conferences",
          ],
      )

    sql_query = "SELECT * FROM past_activities WHERE 1=1"
    params = []

    if cat_filter != "All Categories":
      sql_query += " AND category = ?"
      params.append(cat_filter)

    if search_term.strip():
      sql_query += " AND (title LIKE ? OR speaker LIKE ? OR description LIKE ?)"
      s_param = f"%{search_term.strip()}%"
      params.extend([s_param, s_param, s_param])

    sql_query += " ORDER BY date DESC"

    archive_df = run_query(sql_query, tuple(params))

    if not archive_df.empty:
      for idx, item in archive_df.iterrows():
        with st.expander(
            f"🎥 {item['title']} | {item['category']} ({item['date']})"
        ):
          col_vid, col_desc = st.columns([1, 1])
          with col_vid:
            try:
              st.video(format_youtube_url(item["video_url"]))
            except Exception:
              st.caption(f"Video URL: [{item['video_url']}]({item['video_url']})")
          with col_desc:
            st.markdown(f"**Speaker / Host:** {item['speaker']}")
            st.markdown(f"**Date:** {item['date']}")
            st.markdown(f"**Category:** {item['category']}")
            st.markdown(f"**Description:** {item['description']}")
            st.markdown(
                f"**Sermon Notes / Scripture:** {item['sermon_notes']}"
            )

            if current_role in ["Reverend", "Senior Pastor / Overseer"]:
              if st.button(
                  f"Delete Media Entry #{item['id']}", key=f"del_act_{item['id']}"
              ):
                run_action(
                    "DELETE FROM past_activities WHERE id = ?", (item["id"],)
                )
                log_audit(
                    current_user,
                    f"Deleted past activity media ID {item['id']}",
                    "Media Archive",
                )
                st.success("Activity deleted from archive!")
                st.rerun()
    else:
      st.info("No past activities or sermons match your filter criteria.")

    if current_role in [
        "Reverend",
        "Senior Pastor / Overseer",
        "Pastor",
        "Fellowship & Ministry Leader",
    ]:
      st.markdown("---")
      st.subheader("➕ Add Past Activity / Recorded Service to Archive")
      with st.form("add_past_act_form"):
        col_a1, col_a2 = st.columns(2)
        with col_a1:
          act_title = st.text_input("Activity / Sermon Title")
          act_cat = st.selectbox(
              "Category",
              [
                  "Sunday Sermons",
                  "Kesha & Night Services",
                  "Midweek Fellowship",
                  "Youth & Teens Events",
                  "Special Conferences",
              ],
          )
          act_speaker = st.text_input(
              "Speaker / Facilitator", value="Senior Pastor"
          )
        with col_a2:
          act_date = st.date_input("Event Date", value=datetime.today())
          act_url = st.text_input(
              "Recording Video URL (YouTube / Vimeo / MP4)"
          )
        act_desc = st.text_area("Brief Summary / Description")
        act_notes = st.text_area(
            "Sermon Notes / Scripture References / Downloads"
        )

        submit_act = st.form_submit_button(
            "Publish to Archive", use_container_width=True
        )
        if submit_act:
          if act_title.strip() and act_url.strip():
            run_action(
                "INSERT INTO past_activities (title, category, date, speaker,"
                " video_url, description, sermon_notes) VALUES (?, ?, ?, ?, ?,"
                " ?, ?)",
                (
                    act_title,
                    act_cat,
                    str(act_date),
                    act_speaker,
                    format_youtube_url(act_url),
                    act_desc,
                    act_notes,
                ),
            )
            log_audit(
                current_user,
                f"Archived past activity: '{act_title}'",
                "Media Archive",
            )
            st.success(f"Successfully archived '{act_title}'!")
            st.rerun()
          else:
            st.warning("Please provide at least a title and video URL.")

# ==========================================
# 3. REVEREND MEMBER APPROVAL DESK
# ==========================================
elif app_mode == "👑 Reverend Member Approval Desk":
  if current_role not in ["Reverend", "Senior Pastor / Overseer"]:
    st.error("⛔ Access Denied: Only the Reverend can access the Approval Desk.")
    st.stop()

  st.subheader("👑 Reverend Registration & Permission Approval Desk")
  pending_users = run_query(
      "SELECT * FROM users WHERE approval_status = 'Pending Approval'"
  )
  st.markdown("### ⏳ Pending Approvals Queue")

  if not pending_users.empty:
    st.dataframe(
        pending_users[["full_name", "email", "phone", "role", "verified"]],
        use_container_width=True,
    )
    selected_email = st.selectbox(
        "Select User Email to Review",
        options=pending_users["email"].tolist(),
    )

    col_app1, col_app2 = st.columns(2)
    with col_app1:
      if st.button("✅ Grant Permission (Approve)", use_container_width=True):
        target_user = pending_users[
            pending_users["email"] == selected_email
        ].iloc[0]
        run_action(
            "UPDATE users SET approval_status = 'Approved' WHERE email = ?",
            (selected_email,),
        )

        existing_member = run_query(
            "SELECT id FROM members WHERE email = ?", (selected_email,)
        )
        if existing_member.empty:
          today_str = datetime.today().strftime("%Y-%m-%d")
          run_action(
              "INSERT INTO members (full_name, phone, email, fellowship_group,"
              " department, household, join_date) VALUES (?, ?, ?, 'Canaan"
              " Men', ?, 'Independent', ?)",
              (
                  target_user["full_name"],
                  target_user["phone"] if target_user["phone"] else "N/A",
                  target_user["email"],
                  target_user["role"],
                  today_str,
              ),
          )

        log_audit(
            current_user,
            f"Approved registration for user: {selected_email}",
            "Security",
        )
        st.success(
            f"User {selected_email} approved successfully and added to Active"
            " Members!"
        )
        st.rerun()

    with col_app2:
      if st.button("❌ Reject Permission (Reject)", use_container_width=True):
        run_action(
            "UPDATE users SET approval_status = 'Rejected' WHERE email = ?",
            (selected_email,),
        )
        log_audit(
            current_user,
            f"Rejected registration for user: {selected_email}",
            "Security",
        )
        st.warning(f"User {selected_email} rejected.")
        st.rerun()
  else:
    st.info("No pending user registrations awaiting approval.")

  st.markdown("---")
  st.markdown("### 👥 All Registered System Users")
  all_users = run_query(
      "SELECT full_name, email, phone, role, verified, approval_status FROM"
      " users"
  )
  st.dataframe(all_users, use_container_width=True)

# ==========================================
# 4. WHATSAPP ANNOUNCEMENT BOARD
# ==========================================
elif app_mode == "💬 WhatsApp Announcement Board":
  st.subheader("💬 Canaan Community Announcement Feed")
  announcements = run_query("SELECT * FROM announcements ORDER BY id ASC")

  st.markdown('<div class="whatsapp-chat-box">', unsafe_allow_html=True)
  for _, ann in announcements.iterrows():
    st.markdown(
        f"""
            <div class="chat-bubble">
                <span class="chat-sender">📱 {ann['sender']}</span>
                <span class="chat-time">{ann['timestamp']}</span>
                <div class="chat-msg">{ann['message']}</div>
            </div>
        """,
        unsafe_allow_html=True,
    )
  st.markdown("</div>", unsafe_allow_html=True)

  st.markdown("---")
  with st.form("announcement_form", clear_on_submit=True):
    st.write("📢 **Post New Announcement or Prayer Request**")
    new_msg = st.text_area("Type your message here...")
    post_btn = st.form_submit_button(
        "Send to Community Feed", use_container_width=True
    )
    if post_btn:
      if new_msg.strip() != "":
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        sender_str = f"{current_user} ({current_role})"
        run_action(
            "INSERT INTO announcements (sender, timestamp, message) VALUES (?,"
            " ?, ?)",
            (sender_str, time_str, new_msg),
        )
        log_audit(
            current_user,
            f"Posted announcement: {new_msg[:30]}...",
            "Announcements",
        )
        st.success("Announcement broadcasted successfully!")
        st.rerun()
      else:
        st.warning("Please enter a message.")

# ==========================================
# 5. SMS & WHATSAPP REMINDER CENTER
# ==========================================
elif app_mode == "📱 SMS & WhatsApp Reminders":
  st.subheader("📱 Automated SMS & WhatsApp Broadcast Center")
  with st.form("sms_form"):
    target_audience = st.selectbox(
        "Target Audience",
        [
            "All Registered Members",
            "Canaan Men",
            "Canaan Women",
            "Canaan Youth / Teens",
            "Theology Students",
            "First-Time Visitors",
        ],
    )
    msg_body = st.text_area(
        "Message Template",
        value=(
            "Praise God! Reminder for our fellowship service today at Canaan"
            " The Place Of God Church. Be blessed!"
        ),
    )
    dispatch_btn = st.form_submit_button(
        "Queue & Dispatch Broadcast", use_container_width=True
    )
    if dispatch_btn:
      if msg_body.strip() != "":
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        run_action(
            "INSERT INTO sms_reminders (timestamp, target_audience,"
            " message_body, sent_by, status) VALUES (?, ?, ?, ?, 'Dispatched"
            " Successfully')",
            (time_str, target_audience, msg_body, current_user),
        )
        log_audit(
            current_user,
            f"Dispatched SMS broadcast to {target_audience}",
            "SMS Reminders",
        )
        st.success(
            f"Broadcast successfully queued and sent to {target_audience}!"
        )
        st.rerun()
      else:
        st.warning("Please type a message.")

  st.markdown("---")
  st.subheader("Broadcast History Log")
  sms_logs = run_query(
      "SELECT timestamp, target_audience, message_body, sent_by, status FROM"
      " sms_reminders ORDER BY id DESC"
  )
  if not sms_logs.empty:
    st.dataframe(sms_logs, use_container_width=True)
  else:
    st.info("No SMS reminders sent yet.")

# ==========================================
# 6. COUNSELING & PRAYER TRACKER
# ==========================================
elif app_mode == "🙏 Counseling & Prayer Tracker":
  st.subheader("🙏 Pastoral Counseling & Confidential Prayer Requests")
  with st.form("prayer_form"):
    col1, col2 = st.columns(2)
    with col1:
      req_type = st.selectbox(
          "Request Type",
          [
              "Confidential Prayer Item",
              "One-on-One Counseling Session",
              "Home Visitation Request",
              "Healing & Deliverance",
          ],
      )
      submitter_name = st.text_input(
          "Your Name / Family (Leave blank for anonymous)", value=current_user
      )
    with col2:
      status_val = st.selectbox(
          "Initial Status",
          ["Pending Pastor Review", "Scheduled", "Prayed For / Resolved"],
      )
    details = st.text_area("Request Details / Confidential Notes")
    submit_prayer = st.form_submit_button(
        "Submit Request", use_container_width=True
    )
    if submit_prayer:
      if details.strip() != "":
        date_str = datetime.today().strftime("%Y-%m-%d")
        name_to_save = (
            submitter_name.strip() if submitter_name.strip() else "Anonymous"
        )
        run_action(
            "INSERT INTO counseling_prayer (date, submitted_by, request_type,"
            " details, status) VALUES (?, ?, ?, ?, ?)",
            (date_str, name_to_save, req_type, details, status_val),
        )
        log_audit(
            current_user, f"Submitted prayer request ({req_type})", "Counseling"
        )
        st.success("Your request has been submitted securely.")
        st.rerun()
      else:
        st.warning("Please enter request details.")

  st.markdown("---")
  st.subheader("Active Prayer & Counseling Queue")
  prayers_df = run_query("SELECT * FROM counseling_prayer")
  if not prayers_df.empty:
    st.dataframe(prayers_df, use_container_width=True)
    if current_role in [
        "Reverend",
        "Senior Pastor / Overseer",
        "Pastor",
        "Fellowship & Ministry Leader",
    ]:
      p_id = st.selectbox(
          "Select Request ID to Update Status",
          options=prayers_df["id"].tolist(),
      )
      new_status = st.selectbox(
          "Update Status To",
          ["Pending Pastor Review", "Scheduled", "Prayed For / Resolved"],
      )
      if st.button("Save Status Update", use_container_width=True):
        run_action(
            "UPDATE counseling_prayer SET status = ? WHERE id = ?",
            (new_status, p_id),
        )
        log_audit(
            current_user,
            f"Updated prayer request ID {p_id} status to {new_status}",
            "Counseling",
        )
        st.success("Request status successfully updated!")
        st.rerun()
  else:
    st.info("No requests logged.")

# ==========================================
# 7. VISITOR & NEW CONVERT PIPELINE
# ==========================================
elif app_mode == "🚪 Visitor & New Convert Pipeline":
  st.subheader("🚪 First-Time Visitor & New Convert Integration Pipeline")
  with st.form("visitor_form"):
    col1, col2 = st.columns(2)
    with col1:
      visitor_name = st.text_input("Visitor Full Name")
      visitor_phone = st.text_input("Phone Contact")
    with col2:
      visit_date = st.date_input("First Visit Date", value=datetime.today())
      assigned_leader = st.text_input(
          "Assigned Follow-Up Leader", value=current_user
      )
    integration_status = st.selectbox(
        "Integration Stage",
        [
            "New Visitor (Pending Call)",
            "Contacted / Welcomed",
            "Attended Midweek Fellowship",
            "Fully Integrated Member",
        ],
    )
    save_visitor = st.form_submit_button(
        "Register Visitor", use_container_width=True
    )
    if save_visitor:
      if visitor_name.strip() != "":
        run_action(
            "INSERT INTO visitor_pipeline (visitor_name, phone,"
            " first_visit_date, assigned_leader, integration_status) VALUES"
            " (?, ?, ?, ?, ?)",
            (
                visitor_name,
                visitor_phone,
                str(visit_date),
                assigned_leader,
                integration_status,
            ),
        )
        log_audit(
            current_user, f"Registered visitor: {visitor_name}", "Visitors"
        )
        st.success(f"Visitor {visitor_name} added successfully!")
        st.rerun()
      else:
        st.warning("Please enter visitor's name.")

  st.markdown("---")
  st.subheader("Active Visitor Pipeline Roster")
  visitors_df = run_query("SELECT * FROM visitor_pipeline")
  if not visitors_df.empty:
    st.dataframe(visitors_df, use_container_width=True)
    v_id = st.selectbox(
        "Select Visitor ID to Update Stage", options=visitors_df["id"].tolist()
    )
    updated_stage = st.selectbox(
        "Move to Stage",
        [
            "New Visitor (Pending Call)",
            "Contacted / Welcomed",
            "Attended Midweek Fellowship",
            "Fully Integrated Member",
        ],
        key="upd_stage",
    )
    if st.button("Update Visitor Pipeline Stage", use_container_width=True):
      run_action(
          "UPDATE visitor_pipeline SET integration_status = ? WHERE id = ?",
          (updated_stage, v_id),
      )
      log_audit(
          current_user,
          f"Updated visitor ID {v_id} stage to {updated_stage}",
          "Visitors",
      )
      st.success("Stage updated successfully!")
      st.rerun()
  else:
    st.info("No visitors registered yet.")

# ==========================================
# 8. ASSET & INVENTORY MANAGEMENT
# ==========================================
elif app_mode == "📦 Asset & Inventory Management":
  st.subheader("📦 Church Asset & Equipment Custody Register")
  with st.form("asset_form"):
    col1, col2 = st.columns(2)
    with col1:
      asset_name = st.text_input(
          "Asset Name (e.g., Catering Utensils, Wireless Microphone)"
      )
      serial_num = st.text_input("Serial Number / Asset Tag")
    with col2:
      condition = st.selectbox(
          "Item Condition",
          [
              "Brand New",
              "Good / Working",
              "Needs Maintenance",
              "Damaged / Out of Service",
          ],
      )
      custodian = st.text_input(
          "Current Custodian / Department Holder", value=current_user
      )
    purchase_val = st.number_input(
        "Purchase Value / Estimated Cost (KES)",
        min_value=0.0,
        value=15000.0,
        step=500.0,
    )
    save_asset = st.form_submit_button(
        "Register Asset", use_container_width=True
    )
    if save_asset:
      if asset_name.strip() != "":
        run_action(
            "INSERT INTO church_assets (asset_name, serial_number, condition,"
            " custodian, purchase_value) VALUES (?, ?, ?, ?, ?)",
            (
                asset_name,
                serial_num if serial_num else "N/A",
                condition,
                custodian,
                purchase_val,
            ),
        )
        log_audit(current_user, f"Registered asset: {asset_name}", "Assets")
        st.success(f"Asset {asset_name} added to inventory successfully!")
        st.rerun()
      else:
        st.warning("Please enter asset name.")

  st.markdown("---")
  st.subheader("Church Inventory Master Register")
  assets_df = run_query("SELECT * FROM church_assets")
  if not assets_df.empty:
    total_asset_val = assets_df["purchase_value"].sum()
    st.metric(
        label="Total Estimated Asset Portfolio Value",
        value=f"KES {total_asset_val:,.2f}",
    )
    st.dataframe(assets_df, use_container_width=True)
  else:
    st.info("No assets recorded.")

# ==========================================
# 9. WEEKLY SCHEDULE HUB
# ==========================================
elif app_mode == "🕒 Weekly Schedule Hub":
  st.subheader("📅 Master Order of Services")
  tab1, tab2 = st.tabs(["Sunday Services", "Weekday & Special Services"])
  with tab1:
    st.markdown("""
        * **Morning Glory:** 5:00 AM – 7:00 AM
        * **Sunday School / Teens:** 7:45 AM – 9:30 AM
        * **Main Service:** 10:00 AM – 3:00 PM
        """)
  with tab2:
    st.markdown("""
        * **Daily Morning Glory (Mon – Fri):** 5:00 AM – 6:00 AM
        * **Lunch Hour Service (Mon – Fri):** 12:45 PM – 1:45 PM
        * **Monday:** Intercessory (6:30 PM – 8:30 PM)
        * **Tuesday:** One-on-One with Prophet (8:00 AM – 5:00 PM)
        * **Wednesday:** Fellowship (6:00 PM – 7:00 PM)
        * **Thursday:** Praise & Worship (7:00 PM – 9:00 PM)
        * **Friday:** Intercessory (6:30 PM – 8:30 PM)
        * **Saturday:** Practices (4:00 PM – 6:30 PM) | Theology Class (8:00 PM – 4:00 PM) | Praise & Worship (7:00 PM – 8:30 PM)
        * **Special Event:** Kesha (Every Last Week of the Month, 9:00 PM – 4:00 AM)
        """)

# ==========================================
# 10. FELLOWSHIPS & HOUSEHOLDS
# ==========================================
elif app_mode == "👥 Fellowships & Households":
  st.subheader("🏛️ Canaan Fellowships & Household Directory")
  men_df = run_query(
      "SELECT COUNT(*) as cnt FROM members WHERE fellowship_group = 'Canaan"
      " Men'"
  )
  women_df = run_query(
      "SELECT COUNT(*) as cnt FROM members WHERE fellowship_group = 'Canaan"
      " Women'"
  )
  youth_df = run_query(
      "SELECT COUNT(*) as cnt FROM members WHERE fellowship_group = 'Canaan"
      " Youth / Teens'"
  )

  men_count = men_df.iloc[0]["cnt"] if not men_df.empty else 0
  women_count = women_df.iloc[0]["cnt"] if not women_df.empty else 0
  youth_count = youth_df.iloc[0]["cnt"] if not youth_df.empty else 0

  f_col1, f_col2, f_col3 = st.columns(3)
  with f_col1:
    st.markdown(
        f"""
            <div class="metric-card">
                <h3>Canaan Men</h3>
                <h2>{men_count} Members</h2>
            </div>
        """,
        unsafe_allow_html=True,
    )
  with f_col2:
    st.markdown(
        f"""
            <div class="metric-card" style="border-left-color: #ec4899;">
                <h3>Canaan Women</h3>
                <h2>{women_count} Members</h2>
            </div>
        """,
        unsafe_allow_html=True,
    )
  with f_col3:
    st.markdown(
        f"""
            <div class="metric-card" style="border-left-color: #8b5cf6;">
                <h3>Canaan Youth / Teens</h3>
                <h2>{youth_count} Members</h2>
            </div>
        """,
        unsafe_allow_html=True,
    )

  st.markdown("---")
  members_df = run_query("SELECT * FROM members")
  if not members_df.empty:
    tab_f1, tab_f2 = st.tabs(
        ["View by Fellowship Group", "View by Family Household"]
    )
    with tab_f1:
      selected_fellowship = st.selectbox(
          "Select Fellowship",
          [
              "All Fellowships",
              "Canaan Men",
              "Canaan Women",
              "Canaan Youth / Teens",
          ],
      )
      if selected_fellowship == "All Fellowships":
        st.dataframe(members_df, use_container_width=True)
      else:
        st.dataframe(
            members_df[members_df["fellowship_group"] == selected_fellowship],
            use_container_width=True,
        )
    with tab_f2:
      unique_households = [h for h in members_df["household"].unique() if h]
      selected_house = st.selectbox(
          "Select Household / Family",
          unique_households if unique_households else ["Independent"],
      )
      st.dataframe(
          members_df[members_df["household"] == selected_house],
          use_container_width=True,
      )
  else:
    st.info("No members registered.")

# ==========================================
# 11. ATTENDANCE TRACKER
# ==========================================
elif app_mode == "📝 Attendance Tracker":
  st.subheader("📋 Service Attendance Log")
  with st.form("attendance_form"):
    col1, col2 = st.columns(2)
    with col1:
      att_date = st.date_input("Service Date", value=datetime.today())
      service_name = st.selectbox(
          "Select Service",
          [
              "Sunday Main Service",
              "Sunday School / Teens",
              "Daily Morning Glory",
              "Lunch Hour Service",
              "Intercessory",
              "One-on-One with Prophet",
              "Fellowship",
              "Praise & Worship",
              "Theology Class",
              "Kesha",
          ],
      )
    with col2:
      attendee_count = st.number_input(
          "Number of Attendees", min_value=0, value=50, step=1
      )
      notes = st.text_input("Special Remarks / Guest Speaker")
    submitted = st.form_submit_button(
        "Save Attendance Record", use_container_width=True
    )
    if submitted:
      run_action(
          "INSERT INTO attendance (date, service_name, attendees, notes)"
          " VALUES (?, ?, ?, ?)",
          (str(att_date), service_name, attendee_count, notes),
      )
      log_audit(
          current_user,
          f"Added attendance record for {service_name} ({attendee_count})",
          "Attendance",
      )
      st.success("Attendance saved successfully!")
      st.rerun()

  st.markdown("---")
  st.subheader("Historical Attendance Roster")
  att_df = run_query("SELECT * FROM attendance")
  if not att_df.empty:
    st.dataframe(att_df, use_container_width=True)
    if current_role in ["Reverend", "Senior Pastor / Overseer"]:
      att_id = st.selectbox(
          "Select Row ID to Delete", options=att_df["id"].tolist()
      )
      if st.button(
          "Delete Selected Attendance Record", use_container_width=True
      ):
        run_action("DELETE FROM attendance WHERE id = ?", (att_id,))
        log_audit(
            current_user,
            f"Deleted attendance record ID: {att_id}",
            "Attendance",
        )
        st.success("Record deleted successfully!")
        st.rerun()
  else:
    st.info("No attendance records logged.")

# ==========================================
# 12. MEMBER DIRECTORY
# ==========================================
elif app_mode == "📁 Member Directory":
  st.subheader("📁 Comprehensive Member Directory")
  with st.form("member_form"):
    col1, col2 = st.columns(2)
    with col1:
      full_name = st.text_input("Full Name")
      phone = st.text_input("Phone Number (e.g., +254...)")
      mem_email = st.text_input("Email Address (Optional)")
      household = st.text_input("Household / Family Name (e.g., Kamau Family)")
    with col2:
      fellowship_group = st.selectbox(
          "Fellowship Group",
          ["Canaan Men", "Canaan Women", "Canaan Youth / Teens"],
      )
      department = st.selectbox(
          "Sub-Department / Ministry",
          [
              "Praise & Worship",
              "Intercessory Team",
              "Teens & Sunday School",
              "Theology Class Student",
              "General Member",
              "Ushering Team",
              "Kitchen / Catering",
          ],
      )
      join_date = st.date_input("Registration Date", value=datetime.today())
    add_member = st.form_submit_button(
        "Register Member", use_container_width=True
    )
    if add_member:
      if full_name.strip() != "":
        run_action(
            "INSERT INTO members (full_name, phone, email, fellowship_group,"
            " department, household, join_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                full_name,
                phone if phone else "N/A",
                mem_email if mem_email else "N/A",
                fellowship_group,
                department,
                household if household else "Independent",
                str(join_date),
            ),
        )
        log_audit(current_user, f"Registered new member: {full_name}", "Members")
        st.success(f"Successfully registered {full_name}!")
        st.rerun()
      else:
        st.warning("Please enter a full name.")

  st.markdown("---")
  st.subheader("Registered Member Roster")

  search_mem = st.text_input(
      "🔍 Search Directory by Name or Department", value=""
  )
  if search_mem.strip():
    members_df = run_query(
        "SELECT * FROM members WHERE full_name LIKE ? OR department LIKE ?",
        (f"%{search_mem.strip()}%", f"%{search_mem.strip()}%"),
    )
  else:
    members_df = run_query("SELECT * FROM members")

  if not members_df.empty:
    st.dataframe(members_df, use_container_width=True)
    csv_data = members_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export Member Roster as CSV",
        data=csv_data,
        file_name="canaan_member_directory.csv",
        mime="text/csv",
    )
    if current_role in ["Reverend", "Senior Pastor / Overseer"]:
      mem_id = st.selectbox(
          "Select Member ID to Remove", options=members_df["id"].tolist()
      )
      if st.button("Remove Selected Member", use_container_width=True):
        run_action("DELETE FROM members WHERE id = ?", (mem_id,))
        log_audit(
            current_user, f"Removed member profile ID: {mem_id}", "Members"
        )
        st.success("Member removed successfully!")
        st.rerun()
  else:
    st.info("No members registered.")

# ==========================================
# 13. THEOLOGY & DISCIPLESHIP TRACKER
# ==========================================
elif app_mode == "🎓 Theology & Discipleship":
  st.subheader("🎓 Theology Class Student Portal & Progress")
  with st.form("theology_form"):
    col1, col2 = st.columns(2)
    with col1:
      student_name = st.text_input("Student Name")
      course_unit = st.selectbox(
          "Course Unit",
          [
              "Foundations of Faith",
              "Prophetic Ministry",
              "Homiletics & Preaching",
              "Biblical Greek & Hebrew",
              "Church Administration",
          ],
      )
    with col2:
      assignment_score = st.number_input(
          "Assignment Score (%)", min_value=0.0, max_value=100.0, value=85.0
      )
      exam_score = st.number_input(
          "Exam Score (%)", min_value=0.0, max_value=100.0, value=80.0
      )
      status = st.selectbox(
          "Student Status", ["Active", "Completed", "Deferred"]
      )
    save_theo = st.form_submit_button(
        "Save Student Record", use_container_width=True
    )
    if save_theo:
      if student_name.strip() != "":
        run_action(
            "INSERT INTO theology (student_name, course_unit, assignment_score,"
            " exam_score, status) VALUES (?, ?, ?, ?, ?)",
            (student_name, course_unit, assignment_score, exam_score, status),
        )
        log_audit(
            current_user,
            f"Updated theology grades for {student_name}",
            "Theology",
        )
        st.success("Student academic record updated successfully!")
        st.rerun()
      else:
        st.warning("Please provide a student name.")

  st.markdown("---")
  st.subheader("Enrolled Theology Students Roster")
  theo_df = run_query("SELECT * FROM theology")
  if not theo_df.empty:
    st.dataframe(theo_df, use_container_width=True)
  else:
    st.info("No students enrolled.")

# ==========================================
# 14. FACILITY BOOKING HUB
# ==========================================
elif app_mode == "📅 Facility Booking Hub":
  st.subheader("📅 Facility & Equipment Reservation Hub")
  with st.form("facility_form"):
    col1, col2 = st.columns(2)
    with col1:
      resource_name = st.selectbox(
          "Resource / Facility",
          [
              "Main Sanctuary",
              "Fellowship Hall",
              "Church Kitchen & Dining",
              "Church Sound System",
              "Praise & Worship Instruments",
              "Church Bus / Van",
          ],
      )
      booked_by = st.text_input("Booked By (Leader / Group)", value=current_user)
    with col2:
      booking_date = st.date_input("Booking Date", value=datetime.today())
      time_slot = st.text_input("Time Slot (e.g., 2:00 PM - 5:00 PM)")
    purpose = st.text_input("Purpose of Reservation")
    save_facility = st.form_submit_button(
        "Confirm Booking", use_container_width=True
    )
    if save_facility:
      run_action(
          "INSERT INTO facilities (resource_name, booked_by, date, time_slot,"
          " purpose) VALUES (?, ?, ?, ?, ?)",
          (resource_name, booked_by, str(booking_date), time_slot, purpose),
      )
      log_audit(
          current_user, f"Reserved facility: {resource_name}", "Facilities"
      )
      st.success("Facility reserved successfully!")
      st.rerun()

  st.markdown("---")
  st.subheader("Current Active Bookings")
  fac_df = run_query("SELECT * FROM facilities")
  if not fac_df.empty:
    st.dataframe(fac_df, use_container_width=True)
  else:
    st.info("No active facility bookings.")

# ==========================================
# 15. TITHES & FINANCIAL ANALYTICS
# ==========================================
elif app_mode == "💰 Tithes & Financial Analytics":
  if current_role not in [
      "Reverend",
      "Senior Pastor / Overseer",
      "Church Treasurer",
  ]:
    st.error(
        "⛔ Access Denied: You do not have permission to access Financial"
        " Analytics."
    )
    st.stop()

  st.subheader("💰 Financial Ledger & Interactive Analytics")
  with st.form("finance_form"):
    col1, col2 = st.columns(2)
    with col1:
      fin_date = st.date_input("Transaction Date", value=datetime.today())
      category = st.selectbox(
          "Fund Category",
          [
              "Tithes",
              "Sunday Offerings",
              "Building Fund",
              "Special Offering",
              "Church Expense",
          ],
      )
    with col2:
      amount = st.number_input(
          "Amount (KES)", min_value=0.0, value=1000.0, step=100.0
      )
      recorder = st.text_input(
          "Recorded By (Treasurer Name)", value=current_user
      )
    description = st.text_input("Description / Notes")
    save_fin = st.form_submit_button(
        "Record Transaction", use_container_width=True
    )
    if save_fin:
      run_action(
          "INSERT INTO finance (date, category, amount, recorded_by,"
          " description) VALUES (?, ?, ?, ?, ?)",
          (str(fin_date), category, amount, recorder, description),
      )
      log_audit(
          current_user,
          f"Recorded financial transaction: KES {amount}",
          "Finance",
      )
      st.success("Financial transaction recorded securely!")
      st.rerun()

  st.markdown("---")
  st.subheader("Financial Breakdown & Analytics")
  fin_df = run_query("SELECT * FROM finance")
  if not fin_df.empty:
    total_sum = fin_df["amount"].sum()
    st.metric(
        label="Total Tracked Contributions", value=f"KES {total_sum:,.2f}"
    )
    st.write("📊 **Fund Collection by Category:**")
    chart_series = fin_df.groupby("category")["amount"].sum()
    st.bar_chart(chart_series)
    st.markdown("---")
    st.subheader("Transaction History Ledger")
    st.dataframe(fin_df, use_container_width=True)
    fin_csv = fin_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export Financial Ledger as CSV",
        data=fin_csv,
        file_name="canaan_financial_ledger.csv",
        mime="text/csv",
    )
    if current_role in [
        "Reverend",
        "Senior Pastor / Overseer",
        "Church Treasurer",
    ]:
      fin_id = st.selectbox(
          "Select Transaction ID to Delete", options=fin_df["id"].tolist()
      )
      if st.button("Delete Selected Transaction", use_container_width=True):
        run_action("DELETE FROM finance WHERE id = ?", (fin_id,))
        log_audit(
            current_user, f"Deleted financial entry ID: {fin_id}", "Finance"
        )
        st.warning("Financial entry deleted and logged in audit trail.")
        st.rerun()
  else:
    st.info("No financial transactions recorded.")

# ==========================================
# 16. M-PESA INTEGRATION LEDGER
# ==========================================
elif app_mode == "📲 M-Pesa Integration Ledger":
  if current_role not in [
      "Reverend",
      "Senior Pastor / Overseer",
      "Church Treasurer",
  ]:
    st.error(
        "⛔ Access Denied: You do not have permission to view M-Pesa Ledgers."
    )
    st.stop()

  st.subheader("📲 Automated M-Pesa Paybill / Till Number Feed")
  st.write(
      "Simulate or track incoming M-Pesa transactions for tithes and offerings"
      " in real time."
  )

  with st.form("mpesa_form"):
    col1, col2 = st.columns(2)
    with col1:
      receipt_no = st.text_input("M-Pesa Confirmation Code (e.g., RGH7389LK)")
      sender_name = st.text_input("Sender Name")
    with col2:
      phone_no = st.text_input("Phone Number (+254...)")
      mpesa_amount = st.number_input(
          "Amount Paid (KES)", min_value=0.0, value=500.0
      )
    mpesa_cat = st.selectbox(
        "Designation / Purpose",
        ["Tithes", "Sunday Offerings", "Building Fund", "Special Offering"],
    )

    record_mpesa = st.form_submit_button(
        "Verify & Post M-Pesa Transaction", use_container_width=True
    )
    if record_mpesa:
      if receipt_no.strip() != "" and sender_name.strip() != "":
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today_str = datetime.today().strftime("%Y-%m-%d")

        m_success = run_action(
            "INSERT INTO mpesa_ledger (receipt_no, sender_name, phone, amount,"
            " category, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                receipt_no.strip().upper(),
                sender_name.strip(),
                phone_no.strip(),
                mpesa_amount,
                mpesa_cat,
                ts_str,
            ),
        )

        if m_success:
          run_action(
              "INSERT INTO finance (date, category, amount, recorded_by,"
              " description) VALUES (?, ?, ?, ?, ?)",
              (
                  today_str,
                  mpesa_cat,
                  mpesa_amount,
                  f"M-Pesa Auto ({sender_name.strip()})",
                  f"Code: {receipt_no.strip().upper()}",
              ),
          )

          log_audit(
              current_user,
              f"Received M-Pesa payment: {receipt_no} (KES {mpesa_amount})",
              "M-Pesa Ledger",
          )
          st.success(
              f"M-Pesa transaction {receipt_no} verified and synced with"
              " treasury ledger!"
          )
          st.rerun()
      else:
        st.warning("Please fill in the receipt number and sender name.")

  st.markdown("---")
  st.subheader("M-Pesa Transaction Audit Log")
  mpesa_df = run_query("SELECT * FROM mpesa_ledger")
  if not mpesa_df.empty:
    total_mpesa = mpesa_df["amount"].sum()
    st.metric(
        label="Total M-Pesa Collections", value=f"KES {total_mpesa:,.2f}"
    )
    st.dataframe(mpesa_df, use_container_width=True)
  else:
    st.info("No M-Pesa transactions logged yet.")

# ==========================================
# 17. SYSTEM AUDIT TRAIL
# ==========================================
elif app_mode == "🛡️ System Audit Trail":
  if current_role not in ["Reverend", "Senior Pastor / Overseer"]:
    st.error("⛔ Access Denied: Audit Logs are reserved for Senior Clergy.")
    st.stop()

  st.subheader("🛡️ Administrative Audit Trail")
  st.write(
      "Tracks every security event, data entry, modification, and deletion"
      " performed across the system in real time."
  )
  audit_df = run_query(
      "SELECT timestamp, user, action, module FROM audit_trail ORDER BY id DESC"
  )
  if not audit_df.empty:
    st.dataframe(audit_df, use_container_width=True)
    audit_csv = audit_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export Audit Log as CSV",
        data=audit_csv,
        file_name="canaan_audit_trail.csv",
        mime="text/csv",
    )
  else:
    st.info("No audit logs recorded.")