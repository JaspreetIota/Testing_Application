import streamlit as st
import pandas as pd
import datetime
import os
import re

# ---------- File Paths ----------
DATA_FILE = "test_cases.xlsx"
BASE_DIR = "user_data"
IMAGES_DIR = os.path.join(BASE_DIR, "images")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
PROGRESS_DIR = os.path.join(BASE_DIR, "progress")

# Create folders if not exist
for d in [BASE_DIR, IMAGES_DIR, REPORTS_DIR, PROGRESS_DIR]:
    os.makedirs(d, exist_ok=True)

# ---------- Load Test Cases ----------
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result", "Image Filename"])
    df.to_excel(DATA_FILE, index=False, engine='openpyxl')

test_cases = pd.read_excel(DATA_FILE, engine='openpyxl')

# ---------- Sidebar & User Setup ----------
st.sidebar.title("🧪 Test Case Tracker")
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report"])
user = st.sidebar.text_input("Tester Name").strip()

if not user:
    st.warning("Please enter your Tester Name to continue.")
    st.stop()

# Sanitize username for file/folder usage
user_key = re.sub(r'\W+', '_', user.lower())

# Per user progress file
USER_PROGRESS_FILE = os.path.join(PROGRESS_DIR, f"progress_{user_key}.csv")

# Load user progress or create empty DataFrame
if os.path.exists(USER_PROGRESS_FILE):
    user_progress = pd.read_csv(USER_PROGRESS_FILE)
    if not user_progress.empty:
        user_progress["Date"] = pd.to_datetime(user_progress["Date"], errors='coerce')
else:
    user_progress = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "Remark Image Filename"])

# ---------- Session State keys per user ----------
def session_key(k):
    return f"{k}_{user_key}"

if session_key("tested") not in st.session_state:
    st.session_state[session_key("tested")] = {}
if session_key("remarks") not in st.session_state:
    st.session_state[session_key("remarks")] = {}
if session_key("remark_images") not in st.session_state:
    st.session_state[session_key("remark_images")] = {}

tested = st.session_state[session_key("tested")]
remarks = st.session_state[session_key("remarks")]
remark_images = st.session_state[session_key("remark_images")]

# ---------- Helpers ----------
def save_test_cases(df):
    df.to_excel(DATA_FILE, index=False, engine='openpyxl')

def save_user_progress(df):
    df.to_csv(USER_PROGRESS_FILE, index=False)

def clear_user_run_test_state():
    st.session_state[session_key("tested")] = {}
    st.session_state[session_key("remarks")] = {}
    st.session_state[session_key("remark_images")] = {}

def generate_next_id():
    if test_cases.empty:
        return "TC001"
    ids = test_cases["Test Case ID"].dropna().tolist()
    nums = [int(re.sub(r"\D", "", x)) for x in ids if re.sub(r"\D", "", x).isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"TC{next_num:03d}"

# ---------- Main Pages ----------

if menu == "Run Tests":
    st.title(f"✅ Run Test Cases - User: {user}")

    if st.button("🔄 Refresh Inputs (Clear)"):
        clear_user_run_test_state()
        st.experimental_rerun()

    for idx, row in test_cases.iterrows():
        tc_id = row["Test Case ID"]
        with st.expander(f"{tc_id} - {row['Task']}"):
            st.markdown(f"**Module:** {row['Module']}")
            st.markdown(f"**Page/Field:** {row['Page/Field']}")
            st.markdown(f"**Steps:** {row['Steps']}")
            st.markdown(f"**Expected Result:** {row['Expected Result']}")

            if pd.notna(row.get("Image Filename", "")) and row["Image Filename"]:
                img_path = os.path.join(IMAGES_DIR, row["Image Filename"])
                if os.path.exists(img_path):
                    st.image(img_path, caption="Attached Image", use_column_width=True)

            checked = st.checkbox("Mark as Tested", key=session_key(f"tested_{tc_id}"), value=tested.get(tc_id, False))
            tested[tc_id] = checked

            remark_text = st.text_area("Remarks", key=session_key(f"remark_{tc_id}"), value=remarks.get(tc_id, ""))
            remarks[tc_id] = remark_text

            uploaded_img = st.file_uploader("Attach image with remark (optional)", type=["png", "jpg", "jpeg"], key=session_key(f"remark_img_{tc_id}"))
            if uploaded_img is not None:
                remark_images[tc_id] = uploaded_img
            else:
                if tc_id not in remark_images:
                    remark_images[tc_id] = None

    if st.button("💾 Save Test Progress"):
        any_saved = False
        today = datetime.date.today()

        for tc_id, is_tested in tested.items():
            if is_tested:
                remark = remarks.get(tc_id, "")
                remark_img_file = remark_images.get(tc_id)

                remark_img_filename = ""
                if remark_img_file is not None:
                    safe_name = f"remark_{tc_id}_{user_key}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{remark_img_file.name}"
                    with open(os.path.join(IMAGES_DIR, safe_name), "wb") as f:
                        f.write(remark_img_file.getbuffer())
                    remark_img_filename = safe_name

                # Check if already exists for this TC today
                exists = ((user_progress["Test Case ID"] == tc_id) & (user_progress["Date"].dt.date == today)).any() if not user_progress.empty else False

                if not exists:
                    new_entry = {
                        "Test Case ID": tc_id,
                        "Date": today,
                        "Status": "Tested",
                        "Remarks": remark,
                        "Remark Image Filename": remark_img_filename
                    }
                    user_progress = pd.concat([user_progress, pd.DataFrame([new_entry])], ignore_index=True)
                    any_saved = True

        if any_saved:
            save_user_progress(user_progress)
            st.success("Test progress saved!")
        else:
            st.info("No new test progress to save.")

elif menu == "Edit Test Cases":
    st.title("📝 Edit / Add Test Cases")

    with st.expander("➕ Add New Test Case"):
        new_id = generate_next_id()
        st.text_input("Test Case ID", value=new_id, disabled=True)
        page = st.text_input("Page/Field")
        module = st.text_input("Module")
        task = st.text_input("Task")
        steps = st.text_area("Steps")
        expected = st.text_area("Expected Result")
        image = st.file_uploader("Attach Image (optional)", type=["png", "jpg", "jpeg"])

        if st.button("Add Test Case"):
            image_filename = ""
            if image:
                safe_name = f"testcase_{new_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{image.name}"
                with open(os.path.join(IMAGES_DIR, safe_name), "wb") as f:
                    f.write(image.getbuffer())
                image_filename = safe_name

            new_row = {
                "Test Case ID": new_id,
                "Page/Field": page,
                "Module": module,
                "Task": task,
                "Steps": steps,
                "Expected Result": expected,
                "Image Filename": image_filename
            }
            global test_cases
            test_cases = pd.concat([test_cases, pd.DataFrame([new_row])], ignore_index=True)
            save_test_cases(test_cases)
            st.success("Test case added!")

elif menu == "Progress Dashboard":
    st.title(f"📊 Progress Dashboard - User: {user}")

    if user_progress.empty:
        st.info("No progress data available for you yet.")
    else:
        today = datetime.date.today()
        today_tests = user_progress[user_progress["Date"].dt.date == today]
        week_tests = user_progress[user_progress["Date"] >= pd.to_datetime(today - datetime.timedelta(days=7))]

        st.metric("Tested Today", len(today_tests))
        st.metric("Tested This Week", len(week_tests))
        st.metric("Total Tests Logged", len(user_progress))

        tested_count = user_progress["Test Case ID"].nunique()
        total_count = test_cases["Test Case ID"].nunique()
        st.progress(tested_count / total_count if total_count else 0)

        st.subheader("🗂️ Your Test Case History")
        st.dataframe(user_progress.sort_values(by="Date", ascending=False))

elif menu == "Download Report":
    st.title(f"📄 Generate & Download Report - User: {user}")

    if user_progress.empty:
        st.info("No progress to report.")
    else:
        date_str = datetime.date.today().strftime("%Y%m%d")
        report_file = os.path.join(REPORTS_DIR, f"report_{user_key}_{date_str}.csv")

        user_progress.to_csv(report_file, index=False)
        st.success("Report ready!")

        with open(report_file, "rb") as f:
            st.download_button("📥 Download Report", f, file_name=os.path.basename(report_file), mime="text/csv")
