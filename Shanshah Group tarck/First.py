# app_modern.py
# Streamlit — Group Payment Tracker (Dark Futuristic UI + Charts + Progress)
# Option B: Modern UI (dark, glass, neon accents, subtle animations)
#
# Features:
# - All existing functionality preserved (members, payments, monthly rollover, admin password=1234)
# - Modern visuals: animated header, glass cards, progress bars, monthly trend chart
# - Month-wise logs, member cards, admin add/edit/delete
# - Persistent SQLite DB, random numeric member IDs
#
# Run: streamlit run app_modern.py

import streamlit as st
import sqlite3
import os
import random
from datetime import datetime
import pandas as pd
import numpy as np
from base64 import b64encode

# -------------------------
# Config & DB
# -------------------------
st.set_page_config(page_title="Group Payment Tracker — Modern", layout="wide", page_icon="💳")
st.set_page_config(page_title="Group Payment Tracker", layout="wide", page_icon="💳")
# --- Convert logo to base64 (so it works locally & online)
logo_path = "logo.png"
logo_html = ""

if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        logo_base64 = b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" style="width:250px; height:auto; border-radius:12px; margin-right:15px;">'
else:
    logo_html = "🖼️"

# --- Header layout ---
st.markdown(f"""
    <div style="display:flex; align-items:center; gap:15px; margin-bottom:10px;">
        {logo_html}
        <div>
            <h1 style="
                margin:0;
                font-size:42px;
                font-weight:800;
                background: linear-gradient(90deg, #7c3aed, #06b6d4);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            ">
                Shahanshah Group Collection
            </h1>
            <p style="color:#aaaaaa; font-size:16px; margin-top:-5px;">
                Monthly Payment Management System
            </p>
        </div>
    </div>
""", unsafe_allow_html=True)
BASE_DIR = os.path.dirname(__file__)
DB_FILE = os.path.join(BASE_DIR, "group_tracker.db")

# persistent connection
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# -------------------------
# Schema (safe-create)
# -------------------------
c.execute("""
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    amount REAL DEFAULT 250
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER,
    month INTEGER,
    year INTEGER,
    status TEXT DEFAULT 'Unpaid',
    amount REAL,
    last_updated TEXT,
    FOREIGN KEY(member_id) REFERENCES members(id)
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
conn.commit()

# -------------------------
# Helpers & DB functions (unchanged core logic)
# -------------------------
def now_str():
    return datetime.now().strftime("%d/%m/%Y, %I:%M %p")

def current_month_year_tuple():
    now = datetime.now()
    return now.month, now.year

def current_month_label():
    return datetime.now().strftime("%B %Y")

def generate_unique_id():
    while True:
        new_id = random.randint(10000, 99999)
        c.execute("SELECT 1 FROM members WHERE id=?", (new_id,))
        if not c.fetchone():
            return new_id

def get_members_df():
    return pd.read_sql_query("SELECT * FROM members ORDER BY name COLLATE NOCASE", conn)

def get_payments_df():
    return pd.read_sql_query("""
        SELECT p.id AS payment_id, p.member_id, m.name, p.month, p.year, p.status, p.amount, p.last_updated
        FROM payments p LEFT JOIN members m ON p.member_id = m.id
        ORDER BY p.year DESC, p.month DESC, m.name
    """, conn)

def add_member(name, phone, amount=250.0):
    mid = generate_unique_id()
    c.execute("INSERT INTO members (id, name, phone, amount) VALUES (?, ?, ?, ?)",
              (mid, name, phone, float(amount)))
    conn.commit()
    ensure_payments_for_member_month(mid)

def update_member(member_id, name, phone, amount):
    c.execute("UPDATE members SET name=?, phone=?, amount=? WHERE id=?",
              (name, phone, float(amount), member_id))
    conn.commit()
    month, year = current_month_year_tuple()
    c.execute("UPDATE payments SET amount=?, last_updated=? WHERE member_id=? AND month=? AND year=?",
              (float(amount), now_str(), member_id, month, year))
    conn.commit()

def delete_member(member_id):
    c.execute("DELETE FROM payments WHERE member_id=?", (member_id,))
    c.execute("DELETE FROM members WHERE id=?", (member_id,))
    conn.commit()

def clear_all_data():
    c.execute("DELETE FROM payments")
    c.execute("DELETE FROM members")
    try:
        c.execute("DELETE FROM sqlite_sequence WHERE name='payments'")
    except Exception:
        pass
    conn.commit()

def ensure_payments_for_month():
    month, year = current_month_year_tuple()
    members = c.execute("SELECT id, amount FROM members").fetchall()
    for mid, amt in members:
        c.execute("SELECT 1 FROM payments WHERE member_id=? AND month=? AND year=?", (mid, month, year))
        if not c.fetchone():
            c.execute("INSERT INTO payments (member_id, month, year, status, amount, last_updated) VALUES (?, ?, ?, ?, ?, ?)",
                      (mid, month, year, "Unpaid", float(amt), now_str()))
    conn.commit()

def ensure_payments_for_member_month(member_id):
    month, year = current_month_year_tuple()
    c.execute("SELECT 1 FROM payments WHERE member_id=? AND month=? AND year=?", (member_id, month, year))
    if not c.fetchone():
        c.execute("SELECT amount FROM members WHERE id=?", (member_id,))
        row = c.fetchone()
        amt = float(row[0]) if row else 250.0
        c.execute("INSERT INTO payments (member_id, month, year, status, amount, last_updated) VALUES (?, ?, ?, ?, ?, ?)",
                  (member_id, month, year, "Unpaid", amt, now_str()))
        conn.commit()

def mark_paid_for_member_current_month(member_id):
    month, year = current_month_year_tuple()
    c.execute("UPDATE payments SET status='Paid', last_updated=? WHERE member_id=? AND month=? AND year=?",
              (now_str(), member_id, month, year))
    conn.commit()

def ensure_monthly_rollover():
    month, year = current_month_year_tuple()
    last = c.execute("SELECT value FROM meta WHERE key='last_run_month'").fetchone()
    last_val = last[0] if last else None
    cur_val = f"{month:02d}-{year}"
    if last_val != cur_val:
        ensure_payments_for_month()
        c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('last_run_month', ?)", (cur_val,))
        conn.commit()

# init
ensure_monthly_rollover()

# -------------------------
# Modern Dark Futuristic CSS + small animations
# -------------------------
st.markdown(
    """
    <style>
    :root{
      --bg1: #05060a;
      --glass: rgba(255,255,255,0.03);
      --accent1: #7c3aed;
      --accent2: #06b6d4;
      --muted: #9aa6b2;
      --card-shadow: 0 10px 30px rgba(124,58,237,0.08);
    }
    .stApp { background: linear-gradient(180deg,var(--bg1) 0%, #0b1220 100%); color: #e6eef6; }
    .top-hero {
      display:flex; align-items:center; justify-content:space-between;
      padding:18px; margin-bottom:14px; border-radius:12px;
      background: linear-gradient(90deg, rgba(124,58,237,0.06), rgba(6,182,212,0.03));
      border: 1px solid rgba(255,255,255,0.02);
      box-shadow: 0 6px 24px rgba(2,6,23,0.5);
      backdrop-filter: blur(6px);
    }
    .hero-title { font-size:22px; font-weight:700; letter-spacing:0.2px; }
    .hero-sub { color: var(--muted); font-size:13px; margin-top:4px; }
    .card { background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
            padding:14px; border-radius:12px; border:1px solid rgba(255,255,255,0.03);
            box-shadow: var(--card-shadow); color:#e6eef6; transition: transform .14s ease, box-shadow .14s ease; }
    .card:hover{ transform: translateY(-6px); box-shadow: 0 18px 40px rgba(2,6,23,0.6); }

    /* Buttons general (black text) */
    .stButton>button, button[kind="primary"], .stFormSubmitButton>button {
      background: linear-gradient(90deg,var(--accent1),var(--accent2)) !important;
      color: black !important;
      border: none !important;
      padding: 0.56rem 0.95rem !important;
      border-radius: 10px !important;
      font-weight:700 !important;
      box-shadow: 0 6px 18px rgba(124,58,237,0.08) !important;
    }
    .stButton>button:hover, .stFormSubmitButton>button:hover {
      transform: translateY(-2px) scale(1.02) !important;
      box-shadow: 0 18px 40px rgba(124,58,237,0.12) !important;
    }
    .stDownloadButton > button {
      background: linear-gradient(90deg,var(--accent1),var(--accent2)) !important;
      color: black !important;
      border: none !important;
      padding: 0.56rem 0.95rem !important;
      border-radius: 10px !important;
      font-weight:700 !important;
      box-shadow: 0 6px 18px rgba(124,58,237,0.08) !important;
    }

    /* Paid / Unpaid badges */
    .badge-paid { background: linear-gradient(90deg,#d1fae5,#bbf7d0); color:#064e3b; padding:6px 10px; border-radius:8px; font-weight:700; display:inline-block; }
    .badge-unpaid { background: linear-gradient(90deg,#ffd2d2,#ffb4b4); color:#7f1d1d; padding:6px 10px; border-radius:8px; font-weight:700; display:inline-block; }

    /* small animated bars */
    .progress-wrap { background: rgba(255,255,255,0.03); border-radius:8px; padding:6px; }
    .progress-bar {
      height:10px; border-radius:8px; background: linear-gradient(90deg,var(--accent1),var(--accent2));
      width: 0%; transition: width 0.9s cubic-bezier(.2,.9,.3,1);
    }

    /* small muted text */
    .muted { color: var(--muted); font-size:13px; }

    /* Dataframe color */
    table.dataframe td, table.dataframe th { color: #e6eef6; }

    </style>
    """, unsafe_allow_html=True
)

# -------------------------
# Header / Hero
# -------------------------
col_h1, col_h2 = st.columns([4,1])
with col_h1:
    st.markdown(
        f"""<div class="top-hero">
                <div>
                  <div class="hero-title">💳 Group Payment Tracker — {current_month_label()}</div>
                  <div class="hero-sub">Modern dark dashboard · monthly tracking · quick actions</div>
                </div>
                <div style="text-align:right">
                  <div class="muted">Status: <span style="font-weight:700">Live</span></div>
                  <div style="height:6px"></div>
                  <div class="muted">Admin: 🔒</div>
                </div>
            </div>""", unsafe_allow_html=True)
with col_h2:
    # quick collected metric card
    payments_all = get_payments_df()
    collected_now = 0
    month, year = current_month_year_tuple()
    if not payments_all.empty:
        collected_now = int(payments_all[(payments_all['month'] == month) & (payments_all['year'] == year) & (payments_all['status']=='Paid')]['amount'].sum() or 0)
    st.markdown(f"<div class='card'><div class='muted'>Collected (this month)</div><h3>Rs {collected_now}</h3></div>", unsafe_allow_html=True)

# -------------------------
# Sidebar / Navigation
# -------------------------
st.sidebar.title("⚙️ Controls")
st.sidebar.markdown("Navigate the app")
page = st.sidebar.selectbox("Navigate", ["Members (Public)", "Admin"])

# -------------------------
# Members (public landing)
# -------------------------
if page == "Members (Public)":
    ensure_payments_for_month()
    st.markdown("## 🧾 Members — This Month")
    month, year = current_month_year_tuple()
    q = """
        SELECT p.member_id, m.name, m.phone, p.status, p.amount, p.last_updated
        FROM payments p LEFT JOIN members m ON m.id = p.member_id
        WHERE p.month=? AND p.year=?
        ORDER BY m.name COLLATE NOCASE
    """
    rows = c.execute(q, (month, year)).fetchall()
    if not rows:
        st.info("No payment records for this month. Admin can add members.")
    else:
        # show a progress summary at top
        total_members = len(rows)
        paid_count = sum(1 for r in rows if r[3] == 'Paid')
        pct = int((paid_count / total_members) * 100) if total_members else 0
        st.markdown(f"<div class='card'><div class='muted'>This month progress</div><h3 style='margin:6px 0'>{pct}% collected</h3><div class='muted' style='margin-bottom:8px'>Paid: {paid_count} · Members: {total_members}</div><div class='progress-wrap'><div class='progress-bar' style='width:{pct}%;'></div></div></div>", unsafe_allow_html=True)

        cols = st.columns(2)
        for i, (member_id, name, phone, status, amount, last_updated) in enumerate(rows):
            col = cols[i % 2]
            badge = "<span class='badge-paid'>Paid</span>" if status == "Paid" else "<span class='badge-unpaid'>Unpaid</span>"
            col.markdown(f"""
                <div class='card' style='margin-bottom:12px;'>
                  <div style="display:flex; justify-content:space-between; align-items:center">
                    <div>
                      <h4 style="margin:0">{name} <small class='muted'>({member_id})</small></h4>
                      <div class="muted" style="margin-top:6px">📞 {phone or '-'}</div>
                    </div>
                    <div style="text-align:right">
                      <div style="margin-bottom:6px">{badge}</div>
                      <div class="muted">Rs {int(amount)}</div>
                      <div class="muted" style="font-size:12px; margin-top:6px;">{last_updated or '-'}</div>
                    </div>
                  </div>
                </div>
            """, unsafe_allow_html=True)

# -------------------------
# Admin (password protected)
# -------------------------
elif page == "Admin":
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        st.markdown("## 🔐 Admin Login")
        pwd = st.text_input("Enter admin password:", type="password")
        if st.button("Login"):
            if pwd == "1234":
                st.session_state.admin_logged_in = True
                st.success("Welcome, Admin ✅")
            else:
                st.error("Wrong password")
        st.stop()

    # Admin UI layout
    st.markdown("## 🔒 Admin Panel")
    tab = st.radio("Menu", ["Dashboard", "Members", "Logs", "Settings"], horizontal=True)

    # ---------------- Dashboard ----------------
    if tab == "Dashboard":
        ensure_payments_for_month()
        st.markdown("### Dashboard — Overview")
        month, year = current_month_year_tuple()
        payments_df = get_payments_df()
        members_df = get_members_df()

        total_members = len(members_df)
        paid_count = len(payments_df[(payments_df['month']==month) & (payments_df['year']==year) & (payments_df['status']=='Paid')])
        unpaid_count = total_members - paid_count
        collected = int(payments_df[(payments_df['month']==month) & (payments_df['year']==year) & (payments_df['status']=='Paid')]['amount'].sum() or 0)

        a,b,c,d = st.columns(4)
        a.metric("Members", total_members)
        b.metric("Paid", paid_count)
        c.metric("Unpaid", unpaid_count)
        d.metric("Collected (this month)", f"Rs {collected}")

        st.markdown("---")
        # Trend chart: total collected per month
        if payments_df.empty:
            st.info("No payment records yet.")
        else:
            payments_df['month_label'] = payments_df.apply(lambda r: datetime(int(r['year']), int(r['month']), 1).strftime("%b %Y"), axis=1)
            trend = payments_df[payments_df['status']=='Paid'].groupby('month_label')['amount'].sum().reset_index()
            trend = trend.sort_values(by='month_label')
            if trend.empty:
                st.info("No paid records yet to show trend.")
            else:
                st.markdown("**Trend — Collected per month**")
                st.line_chart(data=trend.set_index('month_label')['amount'])

        st.markdown("---")
        st.markdown("**Recent Payments (this month)**")
        recent = payments_df[(payments_df['month']==month) & (payments_df['year']==year)].sort_values('last_updated', ascending=False)
        if recent.empty:
            st.info("No records this month.")
        else:
            st.dataframe(recent[['member_id','name','status','amount','last_updated']].rename(columns={'member_id':'ID','name':'Name','status':'Status','amount':'Amount','last_updated':'Updated'}), use_container_width=True)

    # ---------------- Members (admin add/edit) ----------------
    elif tab == "Members":
        st.markdown("### 👥 Members — Add / Edit")
        ensure_payments_for_month()
        members_df = get_members_df()

        # Add form
        st.markdown("#### Add New Member")
        with st.form("add_form", clear_on_submit=True):
            na, ph, am = st.columns([3,2,1])
            with na:
                name = st.text_input("Full name")
            with ph:
                phone = st.text_input("Phone (optional)")
            with am:
                amount = st.number_input("Monthly amount (Rs)", value=250.0, min_value=0.0, step=1.0)
            add_clicked = st.form_submit_button("Add Member")
            if add_clicked:
                if not name.strip():
                    st.error("Name required.")
                else:
                    add_member(name.strip(), phone.strip() if phone else None, float(amount))
                    st.success(f"Added {name.strip()} ✅")
                    members_df = get_members_df()

        st.markdown("---")
        st.markdown("#### Edit Existing Member")
        if members_df.empty:
            st.info("No members yet.")
        else:
            sel = st.selectbox("Select member", [f"{r['id']} — {r['name']}" for _, r in members_df.iterrows()], key="admin_edit_sel")
            sel_id = int(sel.split("—")[0].strip())
            rec = members_df[members_df['id'] == sel_id].iloc[0]

            with st.form("edit_form"):
                e1, e2, e3 = st.columns([3,2,1])
                with e1:
                    new_name = st.text_input("Full name", value=rec['name'])
                with e2:
                    new_phone = st.text_input("Phone", value=rec['phone'] or "")
                with e3:
                    new_amount = st.number_input("Monthly amount (Rs)", value=float(rec['amount']), min_value=0.0, step=1.0)
                save = st.form_submit_button("Save Changes")
                if save:
                    update_member(sel_id, new_name.strip(), new_phone.strip(), float(new_amount))
                    st.success("Saved ✅")
                    members_df = get_members_df()

            # actions (toggle paid/unpaid)
            act1, act2 = st.columns(2)
            # Get current payment status for this month
            month, year = current_month_year_tuple()
            cur_status = c.execute("SELECT status FROM payments WHERE member_id=? AND month=? AND year=?",
                       (sel_id, month, year)).fetchone()
            cur_status = cur_status[0] if cur_status else "Unpaid"
            # Toggle button
            with act1:
                if cur_status == "Paid":
                    if st.button("🔁 Mark as Unpaid", key=f"unpaid_{sel_id}"):
                        c.execute("UPDATE payments SET status='Unpaid', last_updated=? WHERE member_id=? AND month=? AND year=?",
                            (now_str(), sel_id, month, year))
                        conn.commit()
                        st.warning("Marked as Unpaid ❌")
                        ensure_payments_for_month()
                else:
                    if st.button("💰 Mark as Paid", key=f"paid_{sel_id}"):
                        mark_paid_for_member_current_month(sel_id)
                        st.success("Marked as Paid ✅")
                        ensure_payments_for_month()

                # Delete button
            with act2:
                if st.button("🗑️ Delete Member", key=f"del_admin_{sel_id}"):
                    delete_member(sel_id)
                    st.warning("Member deleted ❌")
                    members_df = get_members_df()
#----------------------------------------------
            # with act1:
            #     if st.button("Mark Paid (This Month)", key=f"mark_admin_{sel_id}"):
            #         mark_paid_for_member_current_month(sel_id)
            #         st.success("Marked Paid for this month ✅")
            #         ensure_payments_for_month()
            # with act2:
            #     if st.button("Delete Member", key=f"del_admin_{sel_id}"):
            #         delete_member(sel_id)
            #         st.warning("Member deleted ❌")
            #         members_df = get_members_df()

            # member history
            st.markdown("Member payment history")
            hist = pd.read_sql_query("""
                SELECT p.month, p.year, p.status, p.amount, p.last_updated
                FROM payments p
                WHERE p.member_id=?
                ORDER BY p.year DESC, p.month DESC
            """, conn, params=(sel_id,))
            if hist.empty:
                st.info("No history for this member.")
            else:
                hist['Month'] = hist.apply(lambda r: datetime(int(r['year']), int(r['month']), 1).strftime("%B %Y"), axis=1)
                hist_display = hist[['Month','status','amount','last_updated']].rename(columns={'status':'Status','amount':'Amount (Rs)','last_updated':'Last Updated'})
                st.dataframe(hist_display, use_container_width=True)

    # ---------------- Logs ----------------
    elif tab == "Logs":
        st.markdown("### 🧾 Monthly Logs")
        payments_df = get_payments_df()
        if payments_df.empty:
            st.info("No payments recorded yet.")
        else:
            payments_df['month_label'] = payments_df.apply(lambda r: datetime(int(r['year']), int(r['month']), 1).strftime("%B %Y"), axis=1)
            months = payments_df['month_label'].unique().tolist()
            sel_month = st.selectbox("Select month", months, index=0)
            grp = payments_df[payments_df['month_label'] == sel_month]
            total_collected = int(grp[grp['status']=='Paid']['amount'].sum() or 0)
            total_members_month = grp['member_id'].nunique()
            paid_count = len(grp[grp['status']=='Paid'])
            unpaid_count = len(grp[grp['status']=='Unpaid'])

            st.markdown(f"<div class='card'><div class='muted'>Records for</div><h3 style='margin:4px 0'>{sel_month}</h3><div class='muted'>Members: {total_members_month} · Paid: {paid_count} · Unpaid: {unpaid_count}</div><h2 style='margin-top:8px;'>Collected: Rs {total_collected}</h2></div>", unsafe_allow_html=True)
            st.markdown("---")
            disp = grp[['member_id','name','status','amount','last_updated']].rename(columns={'member_id':'Member ID','name':'Name','status':'Status','amount':'Amount (Rs)','last_updated':'Last Updated'})
            st.dataframe(disp.sort_values(['Status','Name'], ascending=[False, True]), use_container_width=True)
            csv_bytes = disp.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV for this month", data=csv_bytes, file_name=f"payments_{sel_month.replace(' ','_')}.csv", mime="text/csv")

    # ---------------- Settings ----------------
    elif tab == "Settings":
        st.markdown("### ⚙️ Settings & Maintenance")
        if st.button("📥 Download DB Backup"):
            with open(DB_FILE, "rb") as f:
                dbdata = f.read()
            st.download_button("Download group_tracker.db", data=dbdata, file_name="group_tracker.db")

        st.markdown("#### ⚠️ Danger Zone")
        confirm = st.checkbox("I understand this will permanently delete all records.")
        if st.button("🧹 Delete All Data", disabled=not confirm):
            clear_all_data()
            st.warning("All records deleted ❌")

        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.success("Logged out.")

# End (DB remains open; Streamlit process covers lifecycle)
# conn.close()
