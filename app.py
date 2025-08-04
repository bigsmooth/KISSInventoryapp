import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
import hashlib
import io

def rerun():
    st.session_state["dummy_rerun_key"] = st.session_state.get("dummy_rerun_key", 0) + 1

# --- Configurable DB Path ---
DB = Path(__file__).parent / "ttt_inventory.db"

def query(sql, params=(), fetch=True):
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.fetchall() if fetch else None

def create_tables():
    query("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        hub TEXT)""")
    query("""CREATE TABLE IF NOT EXISTS inventory (
        sku TEXT,
        hub TEXT,
        quantity INTEGER,
        PRIMARY KEY (sku, hub))""")
    query("""CREATE TABLE IF NOT EXISTS logs (
        timestamp TEXT,
        user TEXT,
        sku TEXT,
        hub TEXT,
        action TEXT,
        qty INTEGER,
        comment TEXT)""")
    query("""CREATE TABLE IF NOT EXISTS sku_info (
        sku TEXT PRIMARY KEY,
        product_name TEXT,
        assigned_hubs TEXT)""")
    query("""CREATE TABLE IF NOT EXISTS shipments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier TEXT,
        tracking TEXT,
        carrier TEXT,
        hub TEXT,
        skus TEXT,
        date TEXT,
        status TEXT)""")
    query("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        message TEXT,
        thread TEXT,
        timestamp TEXT)""")
    query("""CREATE TABLE IF NOT EXISTS count_confirmations (
        username TEXT,
        hub TEXT,
        confirmed_at TEXT)""")

def seed_all_skus():
    # For brevity, add your full SKU seed here or keep existing seeds
    pass

def seed_users():
    users = [
        ("kevin", "Admin", "HQ", "adminpass"),
        ("fox", "Hub Manager", "Hub 2", "foxpass"),
        ("smooth", "Retail", "Retail", "retailpass"),
        ("carmen", "Hub Manager", "Hub 3", "hub3pass"),
        ("slo", "Hub Manager", "Hub 1", "hub1pass"),
        ("vendor", "Supplier", "", "shipit")
    ]
    for u, r, h, p in users:
        pw = hashlib.sha256(p.encode()).hexdigest()
        query("INSERT OR IGNORE INTO users (username, password, role, hub) VALUES (?, ?, ?, ?)", (u, pw, r, h))

def setup_db():
    create_tables()
    seed_all_skus()
    seed_users()

if not Path(DB).exists():
    setup_db()

def login(username, password):
    hashed = hashlib.sha256(password.encode()).hexdigest()
    u = query("SELECT username, role, hub FROM users WHERE username=? AND password=?", (username, hashed))
    return u[0] if u else None

def count_unread(username):
    threads = query("SELECT DISTINCT thread FROM messages WHERE receiver=?", (username,))
    unread = 0
    for t in threads:
        msgs = query("SELECT sender FROM messages WHERE thread=? ORDER BY timestamp DESC LIMIT 1", (t[0],))
        if msgs and msgs[0][0] != username:
            unread += 1
    return unread

if 'user' not in st.session_state:
    st.sidebar.title("🔐 Login")
    u = st.sidebar.text_input("Username")
    p = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        user = login(u, p)
        if user:
            st.session_state.user = user
            rerun()
        else:
            st.sidebar.error("Invalid credentials")
    st.stop()

username, role, hub = st.session_state.user
unread = count_unread(username)
st.sidebar.success(f"Welcome, {username} ({role})")
st.sidebar.markdown(f"📨 **Unread Threads: {unread}**")
if st.sidebar.button("🚪 Logout", key="logout_btn"):
    del st.session_state.user
    rerun()

# --- Menus ---
menus = {
    "Admin": ["Inventory", "Logs", "Shipments", "Messages", "Count", "Assign SKUs", "Create SKU", "Upload SKUs", "User Access"],
    "Hub Manager": ["Inventory", "Update Stock", "Bulk Update", "Messages", "Count"],
    "Retail": ["Inventory", "Update Stock", "Bulk Update", "Messages", "Count"],
    "Supplier": ["Shipments"]
}
menu = st.sidebar.radio("Menu", menus[role], key="menu_radio")

# --- Helper: Refresh Button Wrapper ---
def with_refresh(label, load_func):
    if st.button(f"🔄 Refresh {label}"):
        data = load_func()
        st.session_state[f"{label}_data"] = data
    if f"{label}_data" not in st.session_state:
        st.session_state[f"{label}_data"] = load_func()
    st.dataframe(st.session_state[f"{label}_data"], use_container_width=True)

# --- Inventory View ---
if menu == "Inventory":
    st.header("📦 Inventory View")

    def load_inventory():
        if role == "Admin":
            rows = query("SELECT sku, hub, quantity FROM inventory ORDER BY hub")
        else:
            rows = query("SELECT sku, hub, quantity FROM inventory WHERE hub=?", (hub,))
        df = pd.DataFrame(rows, columns=["SKU", "Hub", "Qty"])
        df['Status'] = df['Qty'].apply(lambda x: "🟥 Low" if x < 10 else "✅ OK")
        sku_filter = st.text_input("Filter by SKU")
        if sku_filter:
            df = df[df["SKU"].str.contains(sku_filter, case=False)]
        return df

    with_refresh("Inventory", load_inventory)

# --- Bulk Update ---
if menu == "Bulk Update":
    st.header("📝 Bulk Inventory Update")

    def load_bulk():
        rows = query("SELECT sku, quantity FROM inventory WHERE hub=?", (hub,))
        return pd.DataFrame(rows, columns=["SKU", "Current Qty"])

    df = load_bulk()

    with st.form("bulk_update_form"):
        st.info("Enter a positive number for IN, negative for OUT. Leave blank to skip. Comments optional.")
        update_data = []
        for idx, row in df.iterrows():
            with st.expander(f"{row['SKU']}  (Current: {row['Current Qty']})", expanded=False):
                adj = st.text_input("Adjust Quantity (+IN / -OUT)", value="", key=f"adj_{idx}_{row['SKU']}", placeholder="+5 or -3")
                comment = st.text_input("Comment", value="", key=f"comm_{idx}_{row['SKU']}", placeholder="Optional")
                update_data.append((row["SKU"], adj, comment))
        submitted = st.form_submit_button("Apply All Updates")

    if submitted:
        errors = []
        results = []
        big_change = False
        any_change = False
        for sku, adj, comment in update_data:
            try:
                n = int(adj.strip()) if adj.strip() else 0
            except:
                n = 0
            if n == 0:
                continue
            any_change = True
            if abs(n) >= 10:
                big_change = True
            record = query("SELECT quantity FROM inventory WHERE sku=? AND hub=?", (sku, hub))
            current = record[0][0] if record else 0
            new_qty = current + n
            if new_qty < 0:
                errors.append(f"❌ Not enough '{sku}' (Now: {current}, Tried: {n})")
                continue
            action = "IN" if n > 0 else "OUT"
            query("""INSERT INTO inventory (sku, hub, quantity)
                     VALUES (?, ?, ?)
                     ON CONFLICT(sku, hub) DO UPDATE SET quantity=excluded.quantity""",
                  (sku, hub, new_qty), fetch=False)
            query("INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), username, sku, hub, action, abs(n), comment), fetch=False)
            results.append(f"{sku}: {action} {abs(n)} (Now: {new_qty})")

        if not any_change:
            st.info("No changes submitted.")
        else:
            if errors:
                st.warning("Some updates failed:\n" + "\n".join(errors))
            if results:
                st.success("✅ Bulk update complete!\n\n" + "\n".join(results))
                logs = query("SELECT timestamp, sku, action, qty, comment FROM logs WHERE hub=? ORDER BY timestamp DESC LIMIT 3", (hub,))
                if logs:
                    st.markdown("#### Last 3 Inventory Actions:")
                    st.table(pd.DataFrame(logs, columns=["Time", "SKU", "Action", "Qty", "Comment"]))
            if big_change:
                st.balloons()

        # Refresh inventory table after updates
        st.session_state.pop("Inventory_data", None)
        st.experimental_rerun()

# --- Update Stock ---
if menu == "Update Stock":
    st.header("\U0001F501 Update Inventory")
    options = query("SELECT sku FROM sku_info WHERE assigned_hubs LIKE ?", (f"%{hub}%",))
    sku_list = [o[0] for o in options]
    sku = st.selectbox("Select SKU", sku_list)
    action = st.radio("Action", ["IN", "OUT"])
    qty = st.number_input("Quantity", min_value=1, step=1)
    comment = st.text_input("Optional Comment")
    if st.button("Submit Update"):
        record = query("SELECT quantity FROM inventory WHERE sku=? AND hub=?", (sku, hub))
        current = record[0][0] if record else 0
        if action == "OUT" and qty > current:
            st.warning("\u274C Not enough stock to remove that amount!")
        else:
            new_qty = current + qty if action == "IN" else current - qty
            query("""INSERT INTO inventory (sku, hub, quantity)
                     VALUES (?, ?, ?)
                     ON CONFLICT(sku, hub) DO UPDATE SET quantity=excluded.quantity""",
                  (sku, hub, new_qty), fetch=False)
            query("INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), username, sku, hub, action, qty, comment), fetch=False)
            st.success(
                f"✅ Inventory updated!  \n**SKU:** {sku}  \n**Hub:** {hub}  \n**Action:** {action}  \n**Qty:** {qty}  \n**New Qty:** {new_qty}"
            )
            st.session_state.pop("Inventory_data", None)
            st.experimental_rerun()

# --- Shipments ---
if menu == "Shipments":
    st.header("🚚 Supplier Shipments")
    if role == "Supplier":
        st.markdown("**Add one or more SKUs for this shipment.**")
        tracking = st.text_input("Tracking Number")
        carrier = st.text_input("Carrier Name")
        hub_dest = st.selectbox("Destination Hub", ["Hub 1", "Hub 2", "Hub 3", "Retail"])
        date = st.date_input("Shipping Date", value=datetime.today())

        if "supplier_skus" not in st.session_state:
            st.session_state["supplier_skus"] = [{"sku": "", "qty": 1}]
        supplier_skus = st.session_state["supplier_skus"]
        all_sku_options = [s[0] for s in query("SELECT sku FROM sku_info")]

        for i, entry in enumerate(supplier_skus):
            cols = st.columns([4,2,1])
            with cols[0]:
                entry["sku"] = st.selectbox(f"SKU {i+1}", all_sku_options, index=all_sku_options.index(entry["sku"]) if entry["sku"] in all_sku_options else 0, key=f"supp_sku_{i}")
            with cols[1]:
                entry["qty"] = st.number_input(f"Qty {i+1}", min_value=1, step=1, key=f"supp_qty_{i}", value=entry["qty"])
            with cols[2]:
                if st.button("Remove", key=f"rmv_sku_{i}"):
                    supplier_skus.pop(i)
                    st.experimental_rerun()
        if st.button("Add Another SKU"):
            supplier_skus.append({"sku": "", "qty": 1})
            st.experimental_rerun()

        st.markdown("---")
        with st.expander("➕ Create New SKU"):
            new_sku = st.text_input("New SKU Name", key="supplier_new_sku")
            if st.button("Add SKU", key="supplier_add_sku"):
                if new_sku.strip():
                    query("INSERT OR IGNORE INTO sku_info (sku, product_name, assigned_hubs) VALUES (?, ?, ?)",
                        (new_sku.strip(), new_sku.strip(), "Hub 1,Hub 2,Hub 3,Retail"), fetch=False)
                    st.success(f"SKU '{new_sku.strip()}' added.")
                    st.experimental_rerun()
                else:
                    st.warning("Enter a SKU name.")

        submitted = st.button("Submit Shipment")
        if submitted:
            if tracking and carrier and all(e["sku"] for e in supplier_skus):
                skus_str = ", ".join([f"{e['sku']} x {e['qty']}" for e in supplier_skus if e["sku"]])
                query("""
                    INSERT INTO shipments (supplier, tracking, carrier, hub, skus, date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (username, tracking.strip(), carrier.strip(), hub_dest, skus_str, str(date), "Pending"), fetch=False)
                st.success("Shipment submitted successfully!")
                st.session_state["supplier_skus"] = [{"sku": "", "qty": 1}]
                st.experimental_rerun()
            else:
                st.error("Please fill out all required fields and SKUs.")

        # Show supplier shipment history with Refresh button
        def load_shipments():
            return pd.DataFrame(query("SELECT * FROM shipments WHERE supplier=? ORDER BY id DESC", (username,)), columns=["ID", "Supplier", "Tracking", "Carrier", "Hub", "SKUs", "Date", "Status"])
        st.markdown("### Your Shipments")
        with st.expander("Refresh Shipments"):
            if st.button("🔄 Refresh Shipments"):
                st.session_state["shipments_data"] = load_shipments()
        if "shipments_data" not in st.session_state:
            st.session_state["shipments_data"] = load_shipments()
        st.dataframe(st.session_state["shipments_data"], use_container_width=True)

    else:
        # Admin, Hub, Retail views for shipments
        rows = query("SELECT * FROM shipments ORDER BY id DESC")
        df = pd.DataFrame(rows, columns=["ID", "Supplier", "Tracking", "Carrier", "Hub", "SKUs", "Date", "Status"])
        st.dataframe(df, use_container_width=True)
        pending = df[df["Status"] == "Pending"]
        if not pending.empty:
            st.subheader("📥 Mark Shipment as Received")
            to_confirm = st.selectbox("Select Pending Shipment", pending["ID"].tolist())
            if st.button("Mark as Received"):
                record = df[df["ID"] == to_confirm].iloc[0]
                sku_list = [s.strip() for s in record["SKUs"].split(",") if s.strip()]
                for sku in sku_list:
                    if ' x ' in sku:
                        name, qty = sku.rsplit(' x ', 1)
                        try:
                            qty = int(qty)
                        except:
                            qty = 1
                    else:
                        name = sku
                        qty = 1
                    current = query("SELECT quantity FROM inventory WHERE sku=? AND hub=?", (name, record["Hub"]))
                    curr_qty = current[0][0] if current else 0
                    new_qty = curr_qty + qty
                    query("INSERT INTO inventory (sku, hub, quantity) VALUES (?, ?, ?) ON CONFLICT(sku, hub) DO UPDATE SET quantity=?",
                          (name, record["Hub"], new_qty, new_qty), fetch=False)
                    query("INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (datetime.now().isoformat(), username, name, record["Hub"], "IN", qty, f"Shipment {record['ID']}"), fetch=False)
                query("UPDATE shipments SET status='Received' WHERE id=?", (to_confirm,), fetch=False)
                st.success("Inventory updated from shipment!")
                st.experimental_rerun()

# --- Messages ---
if menu == "Messages":
    st.header("📢 Internal Messaging")
    if role == "Admin":
        users = [u[0] for u in query("SELECT username FROM users WHERE username != ?", (username,))]
    else:
        users = [u[0] for u in query("SELECT username FROM users WHERE role='Admin'")]
    recipient = st.selectbox("To", users)
    thread = st.text_input("Subject", placeholder="Thread Subject (optional)" if role == "Admin" else "Auto (leave blank)")
    msg = st.text_area("Message", placeholder="Type your message here…")
    if st.button("Send"):
        thread_name = thread.strip() if thread.strip() else f"{username}-{recipient}"
        query("INSERT INTO messages (sender, receiver, message, thread, timestamp) VALUES (?, ?, ?, ?, ?)",
              (username, recipient, msg, thread_name, datetime.now().isoformat()), fetch=False)
        st.success("✅ Message sent!")
        st.experimental_rerun()

    st.markdown("---")
    threads = query("SELECT DISTINCT thread FROM messages WHERE sender=? OR receiver=? ORDER BY timestamp DESC", (username, username))
    for t in threads:
        thread_msgs = query("SELECT timestamp, sender, message FROM messages WHERE thread=? ORDER BY timestamp", (t[0],))
        last_msg = thread_msgs[-1] if thread_msgs else None
        last_from = last_msg[1] if last_msg else ""
        unread = last_from != username
        label = f"🧵 {t[0]}"
        if unread:
            label = f"**🔵 {label}**"
        with st.expander(label):
            for m in thread_msgs:
                st.markdown(f"**{m[1]}** ({m[0]}): {m[2]}")
            reply = st.text_input("Reply", key=f"reply_input_{t[0]}", placeholder="Type your reply here…")
            if st.button("Send Reply", key=f"reply_btn_{t[0]}"):
                last_receiver = [m[1] for m in reversed(thread_msgs) if m[1] != username]
                reply_to = last_receiver[0] if last_receiver else users[0]
                if role == "Admin" or reply_to in users:
                    query("INSERT INTO messages (sender, receiver, message, thread, timestamp) VALUES (?, ?, ?, ?, ?)",
                          (username, reply_to, reply, t[0], datetime.now().isoformat()), fetch=False)
                    st.experimental_rerun()
                else:
                    st.warning("Only reply to HQ is allowed.")

# --- Logs ---
if menu == "Logs":
    st.header("📜 Activity Logs")
    def load_logs():
        logs = query("SELECT * FROM logs ORDER BY timestamp DESC")
        df = pd.DataFrame(logs, columns=["Time", "User", "SKU", "Hub", "Action", "Qty", "Comment"])
        search = st.text_input("🔎 Filter logs", placeholder="Type keyword, SKU, user, action...")
        if search:
            df = df[df.apply(lambda row: search.lower() in row.astype(str).str.lower().to_string(), axis=1)]
        return df

    with_refresh("Logs", load_logs)

# --- Count Mode ---
if menu == "Count":
    st.header("📋 Inventory Count Mode")
    q = "SELECT sku, hub, quantity FROM inventory"
    f = ()
    if role != "Admin":
        q += " WHERE hub=?"
        f = (hub,)

    def load_counts():
        data = query(q, f)
        df = pd.DataFrame(data, columns=["SKU", "Hub", "Qty"])
        df['Status'] = df['Qty'].apply(lambda x: "🟥 Low" if x < 10 else "✅ OK")
        return df

    df = load_counts()
    st.dataframe(df, use_container_width=True)

    if role != "Admin":
        if st.button("✅ Confirm Inventory Count"):
            query("INSERT INTO count_confirmations (username, hub, confirmed_at) VALUES (?, ?, ?)",
                  (username, hub, datetime.now().isoformat()), fetch=False)
            st.success("Count confirmed.")
            st.info("Please refresh to see updates.")
        if st.button("🔄 Refresh Counts"):
            df = load_counts()
            st.dataframe(df, use_container_width=True)

    if role == "Admin":
        confirms = query("SELECT * FROM count_confirmations ORDER BY confirmed_at DESC")
        df_confirm = pd.DataFrame(confirms, columns=["User", "Hub", "Time"])
        st.subheader("Confirmed Counts")
        st.dataframe(df_confirm, use_container_width=True)
        if st.button("🔄 Refresh Confirmations"):
            confirms = query("SELECT * FROM count_confirmations ORDER BY confirmed_at DESC")
            df_confirm = pd.DataFrame(confirms, columns=["User", "Hub", "Time"])
            st.dataframe(df_confirm, use_container_width=True)

# --- Assign SKUs ---
if menu == "Assign SKUs" and role == "Admin":
    st.header("🎯 Assign SKUs to Hubs")
    skus = [s[0] for s in query("SELECT sku FROM sku_info")]
    sku_choice = st.selectbox("Select SKU to Assign", skus)
    hubs = ["Hub 1", "Hub 2", "Hub 3", "Retail"]
    assigned = query("SELECT assigned_hubs FROM sku_info WHERE sku=?", (sku_choice,))
    current = assigned[0][0].split(",") if assigned and assigned[0][0] else []
    new_hubs = st.multiselect("Assign to Hubs", hubs, default=current)
    if st.button("Update Assignments"):
        combined = ",".join(new_hubs)
        query("UPDATE sku_info SET assigned_hubs=? WHERE sku=?", (combined, sku_choice), fetch=False)
        st.success("✅ SKU assignment updated!")
        st.experimental_rerun()

# --- Create SKU ---
if menu == "Create SKU":
    st.header("➕ Create New SKU")
    new_sku = st.text_input("Enter SKU Name")
    if st.button("Create SKU"):
        exists = query("SELECT sku FROM sku_info WHERE sku=?", (new_sku.strip(),))
        if exists:
            st.warning("❌ SKU already exists!")
        elif not new_sku.strip():
            st.warning("❗ Please enter a SKU name.")
        else:
            query("INSERT INTO sku_info (sku, product_name, assigned_hubs) VALUES (?, ?, ?)", (new_sku.strip(), new_sku.strip(), ""), fetch=False)
            st.success(f"✅ SKU '{new_sku}' created successfully!")
            st.experimental_rerun()

# --- Upload SKUs ---
if menu == "Upload SKUs":
    st.header("📥 Upload SKUs from CSV")
    uploaded = st.file_uploader("Upload CSV", type="csv")
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            st.dataframe(df, use_container_width=True)
            count = 0
            for i, row in df.iterrows():
                sku = row.get("sku", "").strip()
                name = row.get("product_name", sku).strip()
                hubs = row.get("assigned_hubs", "").strip()
                if sku:
                    query("INSERT OR IGNORE INTO sku_info (sku, product_name, assigned_hubs) VALUES (?, ?, ?)", (sku, name, hubs), fetch=False)
                    count += 1
            st.success(f"✅ Uploaded {count} SKUs from file.")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"❌ Error processing file: {e}")

# --- User Access ---
if menu == "User Access":
    st.header("🔐 Manage Users")
    users = query("SELECT username, role, hub FROM users")
    df_users = pd.DataFrame(users, columns=["Username", "Role", "Hub"])
    st.dataframe(df_users, use_container_width=True)
    st.subheader("❌ Remove User")
    with st.form("remove_user_form"):
        users = query("SELECT username FROM users WHERE username != ?", (username,))
        user_list = [u[0] for u in users]
        selected_user = st.selectbox("Select User to Remove", user_list, key="remove_user")
        if st.form_submit_button("Request Removal"):
            st.session_state['confirm_remove_user'] = selected_user
        if st.session_state.get('confirm_remove_user') == selected_user:
            if st.button(f"Really remove {selected_user}?"):
                query("DELETE FROM users WHERE username=?", (selected_user,), fetch=False)
                st.success(f"✅ User '{selected_user}' removed.")
                st.session_state.pop('confirm_remove_user')
                st.experimental_rerun()
