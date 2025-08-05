import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
import hashlib
import io

# --- Configurable DB Path ---
DB = Path(__file__).parent / "ttt_inventory.db"

def query(sql, params=(), fetch=True, commit=True):
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        if commit:
            conn.commit()
        return cur.fetchall() if fetch else None

# --- Seed Data: SKUs, Users ---
def seed_all_skus():
    # No deletes: preserves inventory, logs, users
    hub_assignments = {
        "Hub 1": [
            "All American Stripes", "Carolina Blue and White Stripes", "Navy and Silver Stripes",
            "Black and Hot Pink Stripes", "Bubble Gum and White Stripes", "White and Ice Blue Stripes",
            "Imperial Purple and White Stripes", "Hot Pink and White Stripes", "Rainbow Stripes",
            "Twilight Pop", "Juicy Purple", "Lovely Lilac", "Black", "Black and White Stripes"
        ],
        "Hub 2": [
            "Black and Yellow Stripes", "Orange and Black Stripes", "Black and Purple Stripes",
            "Electric Blue and White Stripes", "Blossom Breeze", "Candy Cane Stripes",
            "Plum Solid", "Patriots (Custom)", "Snow Angel (Custom)", "Cranberry Frost (Custom)",
            "Witchy Vibes", "White and Green Stripes", "Black Solid", "Black and White Stripes"
        ],
        "Hub 3": [
            "Black and Grey Stripes", "Black and Green Stripes", "Smoke Grey and Black Stripes",
            "Black and Red Stripes", "Dark Cherry and White Stripes", "Black and Multicolor Stripes",
            "Puerto Rican (Custom)", "Seahawks (Custom)", "PCH (Custom)", "Valentine Socks",
            "Rainbow Stripes", "Thin Black Socks", "Thin Black and White Stripes",
            "Smoke Grey Solid", "Cherry Solid", "Brown Solid", "Wheat and White Stripes",
            "Black Solid", "Black and White Stripes"
        ]
    }
    retail_skus = [
        "Black Solid", "Bubblegum", "Tan Solid", "Hot Pink Solid", "Brown Solid", "Dark Cherry Solid",
        "Winter White Solid", "Coral Orange", "Navy Solid", "Electric Blue Solid", "Celtic Green",
        "Cherry Solid", "Smoke Grey Solid", "Chartreuse Green", "Lovely Lilac", "Carolina Blue Solid",
        "Juicy Purple", "Green & Red Spaced Stripes", "Winter Green Stripes", "Midnight Frost Stripes",
        "Witchy Vibes Stripes", "Light Purple & White Spaced Stripes", "Peppermint Stripes",
        "Red & Black Spaced Stripes", "Gothic Chic Stripes", "Sugar Rush Stripes", "Emerald Onyx Stripes",
        "Pumpkin Spice Stripes", "Pink & White Spaced Stripes", "All American Stripes",
        "Candy Cane Stripes", "Blossom Breeze", "White and Ice Blue Stripes", "Christmas Festive Stripes",
        "White w/ Black stripes", "Navy w/ White stripes", "Cyan w/ White stripes",
        "Celtic Green and White Stripes", "Twilight Pop", "Black and Multicolor Stripes",
        "Black w/ Pink stripes", "Black and Yellow Stripes", "BHM", "Solar Glow", "Navy and Silver Stripes",
        "Cherry and White Stripes", "Wheat and White Stripes", "Brown w/ White stripes",
        "White and Green Stripes", "Coral w/ White stripes", "Imperial Purple and White Stripes",
        "Carolina Blue and White Stripes", "Smoke Grey and White Stripes", "Black w/ White stripes",
        "Bubble Gum and White Stripes", "Dark Cherry and White Stripes", "Hot Pink w/ White stripes",
        "Orange and Black Stripes", "Black and Orange Stripes", "Black w/Red stripes",
        "Smoke Grey w/Black Stripes", "Royal Blue solid", "Black w/Grey stripes", "Black w/Purple stripes",
        "Black w/Rainbow Stripes", "Black and Green Stripes", "Heart Socks", "Shamrock Socks",
        "Plum Solid", "Pumpkin Solid", "PCH", "Cranberry Frost", "Snowy Angel", "Pats", "Seahawks",
        "Black solid (THN)", "White solid (THN)", "Black w/ White stripes (THN)", "Yellow (THN)",
        "Black w/Red stripes (THN)", "Black w/Pink stripes (THN)", "Hot Pink w/White stripes (THN)",
        "Black Solid (SHORT)", "White Solid (SHORT)", "Black and White Stripes (SHORT)"
    ]
    all_skus = set(retail_skus)
    for hub_list in hub_assignments.values():
        all_skus.update(hub_list)
    for sku in sorted(all_skus):
        assigned = [hub for hub, skus in hub_assignments.items() if sku in skus]
        if sku in retail_skus:
            assigned.append("Retail")
        query(
            "INSERT OR REPLACE INTO sku_info (sku, product_name, assigned_hubs) VALUES (?, ?, ?)",
            (sku, sku, ",".join(sorted(set(assigned)))),
            fetch=False,
            commit=True
        )
        for h in assigned:
            query(
                "INSERT OR IGNORE INTO inventory (sku, hub, quantity) VALUES (?, ?, ?)",
                (sku, h, 0),
                fetch=False,
                commit=True
            )
    print("Seeded all SKUs without deleting existing data.")

def seed_users():
    users = [
        ("kevin", "Admin", "HQ", "adminpass"),
        ("fox", "Hub Manager", "Hub 2", "foxpass"),
        ("smooth", "Retail", "Retail", "retailpass"),
        ("carmen", "Hub Manager", "Hub 3", "hub3pass"),
        ("slo", "Hub Manager", "Hub 1", "hub1pass"),
        ("angie", "Supplier", "", "shipit")
    ]
    for u, r, h, p in users:
        pw = hashlib.sha256(p.encode()).hexdigest()
        query(
            "INSERT OR IGNORE INTO users (username, password, role, hub) VALUES (?, ?, ?, ?)",
            (u, pw, r, h),
            fetch=False,
            commit=True
        )

def create_tables():
    query("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        hub TEXT)""", fetch=False, commit=True)
    query("""CREATE TABLE IF NOT EXISTS inventory (
        sku TEXT,
        hub TEXT,
        quantity INTEGER,
        PRIMARY KEY (sku, hub))""", fetch=False, commit=True)
    query("""CREATE TABLE IF NOT EXISTS logs (
        timestamp TEXT,
        user TEXT,
        sku TEXT,
        hub TEXT,
        action TEXT,
        qty INTEGER,
        comment TEXT)""", fetch=False, commit=True)
    query("""CREATE TABLE IF NOT EXISTS sku_info (
        sku TEXT PRIMARY KEY,
        product_name TEXT,
        assigned_hubs TEXT)""", fetch=False, commit=True)
    query("""CREATE TABLE IF NOT EXISTS shipments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier TEXT,
        tracking TEXT,
        carrier TEXT,
        hub TEXT,
        skus TEXT,
        date TEXT,
        status TEXT)""", fetch=False, commit=True)
    query("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        message TEXT,
        thread TEXT,
        timestamp TEXT)""", fetch=False, commit=True)
    query("""CREATE TABLE IF NOT EXISTS count_confirmations (
        username TEXT,
        hub TEXT,
        confirmed_at TEXT)""", fetch=False, commit=True)

def setup_db():
    create_tables()
    existing = query("SELECT sku FROM sku_info LIMIT 1")
    if not existing:
        seed_all_skus()
    seed_users()

if not DB.exists():
    setup_db()
else:
    create_tables()
    seed_users()

def login(username, password):
    hashed = hashlib.sha256(password.encode()).hexdigest()
    user = query(
        "SELECT username, role, hub FROM users WHERE username=? AND password=?",
        (username, hashed)
    )
    return user[0] if user else None

def count_unread(username):
    threads = query("SELECT DISTINCT thread FROM messages WHERE receiver=?", (username,))
    unread = 0
    for t in threads:
        last_msg = query(
            "SELECT sender FROM messages WHERE thread=? ORDER BY timestamp DESC LIMIT 1",
            (t[0],)
        )
        if last_msg and last_msg[0][0] != username:
            unread += 1
    return unread

if "user" not in st.session_state:
    st.sidebar.title("🔐 Login")
    u = st.sidebar.text_input("Username")
    p = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        user = login(u, p)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.sidebar.error("Invalid credentials")
    st.stop()

username, role, hub = st.session_state.user
unread = count_unread(username)

st.sidebar.success(f"Welcome, {username} ({role})")
st.sidebar.markdown(f"📨 **Unread Threads: {unread}**")
if st.sidebar.button("🚪 Logout", key="logout_btn"):
    del st.session_state.user
    st.rerun()

menus = {
    "Admin": ["Inventory", "Logs", "Shipments", "Messages", "Count", "Assign SKUs", "Create SKU", "Upload SKUs", "User Access"],
    "Hub Manager": ["Inventory", "Update Stock", "Bulk Update", "Messages", "Count", "Incoming Shipments"],
    "Retail": ["Inventory", "Update Stock", "Bulk Update", "Messages", "Count"],
    "Supplier": ["Shipments"]
}

menu = st.sidebar.radio("Menu", menus[role], key="menu_radio")

# --- Language Selector ---
if "lang" not in st.session_state:
    st.session_state.lang = "en"
lang = st.sidebar.selectbox("🌐 Language", ["English", "中文"], index=0 if st.session_state.lang=="en" else 1)
st.session_state.lang = "en" if lang=="English" else "zh"

translations = {
    "en": {
        "supplier_shipments": "🚚 Supplier Shipments",
        "add_skus": "Add one or more SKUs for this shipment.",
        "tracking_number": "Tracking Number",
        "carrier": "Carrier Name",
        "destination_hub": "Destination Hub",
        "shipping_date": "Shipping Date",
        "sku": "SKU",
        "qty": "Qty",
        "remove": "Remove",
        "add_another_sku": "Add Another SKU",
        "create_new_sku": "➕ Create New SKU",
        "new_sku_name": "New SKU Name",
        "add_sku": "Add SKU",
        "submit_shipment": "Submit Shipment",
        "shipment_submitted": "Shipment submitted successfully!",
        "fill_out_required": "Please fill out all required fields and SKUs.",
        "your_shipments": "📦 Your Shipments",
        "no_shipments": "You have not submitted any shipments yet.",
        "incoming_shipments": "📦 Incoming Shipments to Your Hub",
        "mark_received": "Mark Shipment as Received",
        "confirm_receipt": "Confirm receipt of shipment",
        "delete_shipment": "Delete Shipment",
        "confirm_delete": "Confirm delete shipment",
        "shipment_deleted": "Shipment deleted.",
        "shipment_confirmed": "Shipment confirmed received and inventory updated."
    },
    "zh": {
        "supplier_shipments": "🚚 供应商发货",
        "add_skus": "为此发货添加一个或多个SKU。",
        "tracking_number": "追踪号码",
        "carrier": "承运人名称",
        "destination_hub": "目的中心",
        "shipping_date": "发货日期",
        "sku": "SKU",
        "qty": "数量",
        "remove": "移除",
        "add_another_sku": "添加另一个SKU",
        "create_new_sku": "➕ 新建SKU",
        "new_sku_name": "新SKU名称",
        "add_sku": "添加SKU",
        "submit_shipment": "提交发货",
        "shipment_submitted": "发货已成功提交！",
        "fill_out_required": "请填写所有必填字段和SKU。",
        "your_shipments": "📦 您的发货记录",
        "no_shipments": "您还没有提交任何发货。",
        "incoming_shipments": "📦 您中心的待发货记录",
        "mark_received": "标记发货为已收到",
        "confirm_receipt": "确认收货",
        "delete_shipment": "删除发货",
        "confirm_delete": "确认删除发货",
        "shipment_deleted": "发货已删除。",
        "shipment_confirmed": "发货已确认收到，库存已更新。"
    }
}

def T(key):
    return translations[st.session_state.lang].get(key, key)

# --- Shipments ---
if menu == "Shipments":
    st.header(T("supplier_shipments"))
    if role == "Supplier":
        tracking = st.text_input(T("tracking_number"))
        carrier = st.text_input(T("carrier"))
        hub_dest = st.selectbox(T("destination_hub"), ["Hub 1", "Hub 2", "Hub 3", "Retail"])
        date = st.date_input(T("shipping_date"), value=datetime.today())
        if "supplier_skus" not in st.session_state:
            st.session_state["supplier_skus"] = [{"sku": "", "qty": 1}]
        supplier_skus = st.session_state["supplier_skus"]
        all_sku_options = [s[0] for s in query("SELECT sku FROM sku_info")]
        for i, entry in enumerate(supplier_skus):
            cols = st.columns([4, 2, 1])
            with cols[0]:
                entry["sku"] = st.selectbox(f"{T('sku')} {i+1}", all_sku_options, index=all_sku_options.index(entry["sku"]) if entry["sku"] in all_sku_options else 0, key=f"supp_sku_{i}")
            with cols[1]:
                entry["qty"] = st.number_input(f"{T('qty')} {i+1}", min_value=1, step=1, key=f"supp_qty_{i}", value=entry["qty"])
            with cols[2]:
                if st.button(T("remove"), key=f"rmv_sku_{i}"):
                    supplier_skus.pop(i)
                    st.rerun()
        if st.button(T("add_another_sku")):
            supplier_skus.append({"sku": "", "qty": 1})
            st.rerun()
        st.markdown("---")
        with st.expander(T("create_new_sku")):
            new_sku = st.text_input(T("new_sku_name"), key="supplier_new_sku")
            if st.button(T("add_sku"), key="supplier_add_sku"):
                if new_sku.strip():
                    query(
                        "INSERT OR IGNORE INTO sku_info (sku, product_name, assigned_hubs) VALUES (?, ?, ?)",
                        (new_sku.strip(), new_sku.strip(), "Hub 1,Hub 2,Hub 3,Retail"),
                        fetch=False,
                        commit=True
                    )
                    st.success(f"SKU '{new_sku.strip()}' added.")
                    st.rerun()
                else:
                    st.warning("Enter a SKU name.")
        submitted = st.button(T("submit_shipment"))
        if submitted:
            if tracking and carrier and all(e["sku"] for e in supplier_skus):
                skus_str = ", ".join([f"{e['sku']} x {e['qty']}" for e in supplier_skus if e["sku"]])
                query(
                    "INSERT INTO shipments (supplier, tracking, carrier, hub, skus, date, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (username, tracking.strip(), carrier.strip(), hub_dest, skus_str, str(date), "Pending"),
                    fetch=False,
                    commit=True
                )
                st.success(T("shipment_submitted"))
                st.session_state["supplier_skus"] = [{"sku": "", "qty": 1}]
                st.rerun()
            else:
                st.error(T("fill_out_required"))

        # Supplier shipment history & delete option
        my_shipments = query("SELECT * FROM shipments WHERE supplier=? AND status!='Deleted' ORDER BY id DESC", (username,))
        st.markdown("### " + T("your_shipments"))
        if my_shipments:
            df_my = pd.DataFrame(my_shipments, columns=["ID", "Supplier", "Tracking", "Carrier", "Hub", "SKUs", "Date", "Status"])
            for idx, row in df_my.iterrows():
                with st.expander(f"Shipment ID {row['ID']} - Status: {row['Status']}"):
                    st.write(f"Tracking: {row['Tracking']}")
                    st.write(f"Carrier: {row['Carrier']}")
                    st.write(f"Hub: {row['Hub']}")
                    st.write(f"SKUs: {row['SKUs']}")
                    st.write(f"Date: {row['Date']}")
                    if row['Status'] == "Pending":
                        if st.button(f"Delete Shipment {row['ID']}"):
                            query("UPDATE shipments SET status='Deleted' WHERE id=?", (row['ID'],), fetch=False, commit=True)
                            st.success(f"Shipment {row['ID']} deleted.")
                            st.rerun()
        else:
            st.info(T("no_shipments"))

    else:
        # Admin and others see all shipments except Deleted
        rows = query("SELECT * FROM shipments WHERE status!='Deleted' ORDER BY id DESC")
        df = pd.DataFrame(rows, columns=["ID", "Supplier", "Tracking", "Carrier", "Hub", "SKUs", "Date", "Status"])
        st.dataframe(df, use_container_width=True)
        pending = df[df["Status"] == "Pending"]
        if not pending.empty:
            st.subheader(T("mark_received"))
            to_confirm = st.selectbox("Select Pending Shipment", pending["ID"].tolist())
            confirm = st.checkbox(T("confirm_receipt"))
            if st.button(T("mark_received")):
                if confirm:
                    record = df[df["ID"] == to_confirm].iloc[0]
                    sku_list = [s.strip() for s in record["SKUs"].split(",") if s.strip()]
                    for sku in sku_list:
                        if " x " in sku:
                            name, qty = sku.rsplit(" x ", 1)
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
                        query(
                            "INSERT INTO inventory (sku, hub, quantity) VALUES (?, ?, ?) ON CONFLICT(sku, hub) DO UPDATE SET quantity=?",
                            (name, record["Hub"], new_qty, new_qty),
                            fetch=False,
                            commit=True
                        )
                        query(
                            "INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (datetime.now().isoformat(), username, name, record["Hub"], "IN", qty, f"Shipment {record['ID']}"),
                            fetch=False,
                            commit=True
                        )
                    query("UPDATE shipments SET status='Received' WHERE id=?", (to_confirm,), fetch=False, commit=True)
                    st.success("Inventory updated from shipment!")
                    st.rerun()

        # Admin delete shipment option
        if role == "Admin":
            st.markdown("---")
            st.subheader(T("delete_shipment"))
            delete_id = st.selectbox("Select Shipment to Delete", df["ID"].tolist())
            confirm_del = st.checkbox(T("confirm_delete"))
            if st.button(T("delete_shipment")):
                if confirm_del:
                    query("UPDATE shipments SET status='Deleted' WHERE id=?", (delete_id,), fetch=False, commit=True)
                    st.success(T("shipment_deleted"))
                    st.rerun()

# --- Incoming Shipments for Hub Managers ---
if menu == "Incoming Shipments" and role == "Hub Manager":
    st.header(T("incoming_shipments"))
    incoming = query("SELECT * FROM shipments WHERE hub=? AND status='Pending' ORDER BY date DESC", (hub,))
    if incoming:
        df_in = pd.DataFrame(incoming, columns=["ID", "Supplier", "Tracking", "Carrier", "Hub", "SKUs", "Date", "Status"])
        for idx, row in df_in.iterrows():
            with st.expander(f"Shipment ID {row['ID']} from {row['Supplier']}"):
                st.write(f"Tracking: {row['Tracking']}")
                st.write(f"Carrier: {row['Carrier']}")
                st.write(f"SKUs: {row['SKUs']}")
                st.write(f"Date: {row['Date']}")
                confirm = st.checkbox(f"{T('mark_received')} {row['ID']}", key=f"confirm_{row['ID']}")
                if confirm:
                    sku_list = [s.strip() for s in row["SKUs"].split(",") if s.strip()]
                    for sku in sku_list:
                        if " x " in sku:
                            name, qty = sku.rsplit(" x ", 1)
                            try:
                                qty = int(qty)
                            except:
                                qty = 1
                        else:
                            name = sku
                            qty = 1
                        current = query("SELECT quantity FROM inventory WHERE sku=? AND hub=?", (name, hub))
                        curr_qty = current[0][0] if current else 0
                        new_qty = curr_qty + qty
                        query(
                            "INSERT INTO inventory (sku, hub, quantity) VALUES (?, ?, ?) ON CONFLICT(sku, hub) DO UPDATE SET quantity=?",
                            (name, hub, new_qty, new_qty),
                            fetch=False,
                            commit=True
                        )
                        query(
                            "INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (datetime.now().isoformat(), username, name, hub, "IN", qty, f"Shipment {row['ID']}"),
                            fetch=False,
                            commit=True
                        )
                    query("UPDATE shipments SET status='Received' WHERE id=?", (row['ID'],), fetch=False, commit=True)
                    st.success(f"{T('shipment_confirmed')}")
                    st.rerun()
    else:
        st.info("No pending shipments for your hub.")

# --- Messages ---
if menu == "Messages":
    st.header("📢 Internal Messaging")
    if role == "Admin":
        users = [u[0] for u in query("SELECT username FROM users WHERE username != ?", (username,))]
        to_label = "To (user):"
        subject_placeholder = "Thread Subject (optional)"
    else:
        users = [u[0] for u in query("SELECT username FROM users WHERE role='Admin'")]
        to_label = "To HQ:"
        subject_placeholder = "Auto (leave blank)"
    st.subheader("Send New Message")
    recipient = st.selectbox(to_label, users)
    thread = st.text_input("Subject", placeholder=subject_placeholder)
    msg = st.text_area("Message", placeholder="Type your message here…")
    if st.button("Send"):
        auto_thread = thread.strip() if thread.strip() else f"{username}-{recipient}"
        query(
            "INSERT INTO messages (sender, receiver, message, thread, timestamp) VALUES (?, ?, ?, ?, ?)",
            (username, recipient, msg, auto_thread, datetime.now().isoformat()),
            fetch=False,
            commit=True
        )
        st.success("✅ Message sent!")
        st.rerun()

    st.markdown("---")
    st.subheader("📨 Your Threads")
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
                    query(
                        "INSERT INTO messages (sender, receiver, message, thread, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (username, reply_to, reply, t[0], datetime.now().isoformat()),
                        fetch=False,
                        commit=True
                    )
                    st.rerun()
                else:
                    st.warning("Only reply to HQ is allowed.")

# --- Logs ---
if menu == "Logs":
    st.header("📜 Activity Logs")
    logs = query("SELECT * FROM logs ORDER BY timestamp DESC")
    df = pd.DataFrame(logs, columns=["Time", "User", "SKU", "Hub", "Action", "Qty", "Comment"])

    search = st.text_input("🔎 Filter logs", placeholder="Type keyword, SKU, user, action...")
    if search:
        df = df[df.apply(lambda row: search.lower() in row.astype(str).str.lower().to_string(), axis=1)]

    def highlight_row(row):
        color = ''
        if row['Action'] == 'OUT' and row['Qty'] > 0:
            color = 'background-color: #f9dada;'
        elif row['Qty'] >= 10:
            color = 'background-color: #e1faea;'
        return [color] * len(row)

    st.dataframe(df.style.apply(highlight_row, axis=1), use_container_width=True)

    buff = io.BytesIO()
    df.to_csv(buff, index=False)
    st.download_button("📥 Download CSV of Logs", buff.getvalue(), "logs.csv", "text/csv")

# --- Count Mode ---
if menu == "Count":
    st.header("📋 Inventory Count Mode")
    q = "SELECT sku, hub, quantity FROM inventory"
    f = ()
    if role != "Admin":
        q += " WHERE hub=?"
        f = (hub,)
    
    def load_data():
        data = query(q, f)
        df = pd.DataFrame(data, columns=["SKU", "Hub", "Qty"])
        df['Status'] = df['Qty'].apply(lambda x: "🟥 Low" if x < 10 else "✅ OK")
        return df
    
    df = load_data()
    st.dataframe(df, use_container_width=True)
    
    if role != "Admin":
        if st.button("✅ Confirm Inventory Count"):
            query("INSERT INTO count_confirmations (username, hub, confirmed_at) VALUES (?, ?, ?)",
                  (username, hub, datetime.now().isoformat()), fetch=False, commit=True)
            st.success("Count confirmed.")
            st.info("Please refresh the page to see updates.")
        
        if st.button("🔄 Refresh"):
            st.rerun()
    
    if role == "Admin":
        confirms = query("SELECT * FROM count_confirmations ORDER BY confirmed_at DESC")
        df_confirm = pd.DataFrame(confirms, columns=["User", "Hub", "Time"])
        st.subheader("Confirmed Counts")
        st.dataframe(df_confirm, use_container_width=True)
        if st.button("🔄 Refresh Confirmations"):
            st.rerun()

# --- Inventory ---
if menu == "Inventory":
    st.header("📦 Inventory View")
    if role == "Admin":
        rows = query("SELECT sku, hub, quantity FROM inventory ORDER BY hub")
    else:
        rows = query("SELECT sku, hub, quantity FROM inventory WHERE hub=?", (hub,))
    df = pd.DataFrame(rows, columns=["SKU", "Hub", "Qty"])
    df['Status'] = df['Qty'].apply(lambda x: "🟥 Low" if x < 10 else "✅ OK")
    sku_filter = st.text_input("Filter by SKU")
    if sku_filter:
        df = df[df["SKU"].str.contains(sku_filter, case=False)]
    st.dataframe(df, use_container_width=True)
    buff = io.StringIO()
    df.to_csv(buff, index=False)
    st.download_button("📥 Export Inventory", buff.getvalue(), "inventory.csv", "text/csv")

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
            query(
                """INSERT INTO inventory (sku, hub, quantity) VALUES (?, ?, ?)
                   ON CONFLICT(sku, hub) DO UPDATE SET quantity=excluded.quantity""",
                (sku, hub, new_qty),
                fetch=False,
                commit=True
            )
            query(
                "INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), username, sku, hub, action, qty, comment),
                fetch=False,
                commit=True
            )
            st.success(
                f"✅ Inventory updated!  \n**SKU:** {sku}  \n**Hub:** {hub}  \n**Action:** {action}  \n**Qty:** {qty}  \n**New Qty:** {new_qty}"
            )
            st.rerun()

# --- Bulk Update ---
if menu == "Bulk Update":
    st.header("📝 Bulk Inventory Update")
    rows = query("SELECT sku, quantity FROM inventory WHERE hub=?", (hub,))
    df = pd.DataFrame(rows, columns=["SKU", "Current Qty"])

    with st.form("bulk_update_form"):
        st.info("Enter a positive number for IN, negative for OUT. Leave blank to skip. Comments optional.")
        update_data = []
        for idx, row in df.iterrows():
            with st.expander(f"{row['SKU']}  (Current: {row['Current Qty']})", expanded=False):
                adj = st.text_input(
                    "Adjust Quantity (+IN / -OUT)", 
                    value="", 
                    key=f"adj_{idx}_{row['SKU']}",
                    placeholder="+5 or -3"
                )
                comment = st.text_input(
                    "Comment", 
                    value="", 
                    key=f"comm_{idx}_{row['SKU']}", 
                    placeholder="Optional"
                )
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
            query(
                """INSERT INTO inventory (sku, hub, quantity) VALUES (?, ?, ?)
                   ON CONFLICT(sku, hub) DO UPDATE SET quantity=excluded.quantity""",
                (sku, hub, new_qty),
                fetch=False,
                commit=True
            )
            query(
                "INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), username, sku, hub, action, abs(n), comment),
                fetch=False,
                commit=True
            )
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
        st.rerun()

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
            query(
                "INSERT INTO sku_info (sku, product_name, assigned_hubs) VALUES (?, ?, ?)",
                (new_sku.strip(), new_sku.strip(), ""),
                fetch=False,
                commit=True
            )
            st.success(f"✅ SKU '{new_sku}' created successfully!")
            st.rerun()

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
                    query(
                        "INSERT OR IGNORE INTO sku_info (sku, product_name, assigned_hubs) VALUES (?, ?, ?)",
                        (sku, name, hubs),
                        fetch=False,
                        commit=True
                    )
                    count += 1
            st.success(f"✅ Uploaded {count} SKUs from file.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error processing file: {e}")

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
        query("UPDATE sku_info SET assigned_hubs=? WHERE sku=?", (combined, sku_choice), fetch=False, commit=True)
        st.success("✅ SKU assignment updated!")
        st.rerun()

# --- User Access ---
if menu == "User Access":
    st.header("🔐 Manage Users")
    users = query("SELECT username, role, hub FROM users")
    df_users = pd.DataFrame(users, columns=["Username", "Role", "Hub"])
    st.dataframe(df_users, use_container_width=True)
    st.subheader("❌ Remove User")
    with st.form("remove_user_form"):
    selected_user = st.selectbox("Select User to Remove", user_list)
    submitted = st.form_submit_button("Request Removal")

    if submitted:
    st.session_state['confirm_remove_user'] = selected_user

    if st.session_state.get('confirm_remove_user') == selected_user:
    if st.button(f"Really remove {selected_user}?"):
        query("DELETE FROM users WHERE username=?", (selected_user,), fetch=False)
        st.success(f"✅ User '{selected_user}' removed.")
        st.session_state.pop('confirm_remove_user')
        st.rerun()

