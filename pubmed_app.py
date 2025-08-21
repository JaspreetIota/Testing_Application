import streamlit as st
import pandas as pd
import datetime
import os
import re

# ---------- CONFIG ----------
TEST_CASES_FILE = "test_cases.xlsx"
PROGRESS_DIR = "progress"
IMAGE_DIR = "images"

os.makedirs(PROGRESS_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# ---------- LOAD USER ----------
st.sidebar.title("🧪 Test Case Tracker")
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report"])
user = st.sidebar.text_input("Tester Name", value="Tester").strip()
if not user:
    st.warning("Please enter your name.")
    st.stop()

# ---------- FILE PATH ----------
def get_user_progress_file(user):
    safe_user = re.sub(r'\W+', '_', user)
    return os.path.join(PROGRESS_DIR, f"{safe_user}_progress.csv")

progress_file = get_user_progress_file(user)

# ---------- LOAD TEST CASES ----------
if not os.path.exists(TEST_CASES_FILE):
    pd.DataFrame(columns=["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result", "Image Filename"]).to_excel(TEST_CASES_FILE, index=False)

test_cases = pd.read_excel(TEST_CASES_FILE, engine='openpyxl')
if "Image Filename" not in test_cases.columns:
    test_cases["Image Filename"] = ""

# ---------- LOAD PROGRESS ----------
if os.path.exists(progress_file):
    progress = pd.read_csv(progress_file)
    if not progress.empty:
        progress["Date"] = pd.to_datetime(progress["Date"], errors='coerce')
else:
    progress = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"])

def save_progress():
    progress.to_csv(progress_file, index=False)

def sanitize_filename(filename):
    return re.sub(r'[^\w\-_\. ]', '_', filename)

def update_progress(tc_id, date, status, remarks, user, remark_img_file=None):
    global progress
    filtered = progress[
        (progress["Test Case ID"] == tc_id) &
        (progress["Date"].dt.date == date) &
        (progress["User"] == user)
    ]
    remark_img_filename = ""

    if not filtered.empty:
        idx = filtered.index[-1]
        if remark_img_file:
            safe_img_name = f"{tc_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{sanitize_filename(remark_img_file.name)}"
            image_path = os.path.join(IMAGE_DIR, safe_img_name)
            with open(image_path, "wb") as f:
                f.write(remark_img_file.getbuffer())
            remark_img_filename = safe_img_name
        else:
            remark_img_filename = progress.at[idx, "Remark Image Filename"]

        progress.at[idx, "Remarks"] = remarks
        progress.at[idx, "Remark Image Filename"] = remark_img_filename
        progress.at[idx, "Date"] = datetime.datetime.now()
        progress.at[idx, "Status"] = status
        progress.at[idx, "User"] = user
    else:
        if remark_img_file:
            safe_img_name = f"{tc_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{sanitize_filename(remark_img_file.name)}"
            image_path = os.path.join(IMAGE_DIR, safe_img_name)
            with open(image_path, "wb") as f:
                f.write(remark_img_file.getbuffer())
            remark_img_filename = safe_img_name

        new_entry = {
            "Test Case ID": tc_id,
            "Date": datetime.datetime.now(),
            "Status": status,
            "Remarks": remarks,
            "User": user,
            "Remark Image Filename": remark_img_filename
        }
        progress.loc[len(progress)] = new_entry

    save_progress()

# ---------- RUN TESTS ----------
if menu == "Run Tests":
    st.title("✅ Run Test Cases")

    # View toggle
    view_mode = st.radio("Select View Mode", ["Expanded View", "Table View"], index=0)

    today = datetime.date.today()
    today_progress = progress[
        (progress["Date"].dt.date == today) & (progress["User"] == user)
    ].copy()

    progress_map = {
        row["Test Case ID"]: row for _, row in today_progress.iterrows()
    }

    if view_mode == "Expanded View":
        for _, row in test_cases.iterrows():
            tc_id = row['Test Case ID']
            with st.expander(f"{tc_id} - {row['Task']}", expanded=True):
                st.markdown(f"**Module:** {row['Module']}")
                st.markdown(f"**Page/Field:** {row['Page/Field']}")
                st.markdown(f"**Steps:** {row['Steps']}")
                st.markdown(f"**Expected Result:** {row['Expected Result']}")

                if pd.notna(row.get("Image Filename", "")) and row["Image Filename"]:
                    img_path = os.path.join(IMAGE_DIR, row["Image Filename"])
                    if os.path.exists(img_path):
                        st.image(img_path, caption="Attached Image")

                prog_entry = progress_map.get(tc_id)
                tested_key = f"{tc_id}_tested"
                remark_key = f"{tc_id}_remark"
                file_key = f"{tc_id}_file"

                if tested_key not in st.session_state:
                    st.session_state[tested_key] = prog_entry is not None and prog_entry["Status"] == "Tested"
                if remark_key not in st.session_state:
                    st.session_state[remark_key] = prog_entry["Remarks"] if prog_entry else ""

                tested = st.checkbox("Mark as Tested", key=tested_key)
                remark = st.text_area("Remarks", value=st.session_state[remark_key], key=remark_key)
                remark_img = st.file_uploader("Attach image (optional)", type=["jpg", "jpeg", "png"], key=file_key)

                if tested:
                    update_progress(tc_id, today, "Tested", remark, user, remark_img)
                    st.success("Auto-saved!")
                else:
                    update_progress(tc_id, today, "Not Tested", remark, user, remark_img)

    elif view_mode == "Table View":
        st.write("Mark test cases as tested, add remarks and upload images below. Changes auto-save.")

        for _, row in test_cases.iterrows():
            tc_id = row["Test Case ID"]
            st.markdown(f"---\n**{tc_id} - {row['Task']}**")

            prog_entry = progress_map.get(tc_id)
            tested_key = f"{tc_id}_table_tested"
            remark_key = f"{tc_id}_table_remark"
            file_key = f"{tc_id}_table_file"

            if tested_key not in st.session_state:
                st.session_state[tested_key] = prog_entry is not None and prog_entry["Status"] == "Tested"
            if remark_key not in st.session_state:
                st.session_state[remark_key] = prog_entry["Remarks"] if prog_entry else ""

            col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
            with col1:
                tested = st.checkbox("", key=tested_key)
            with col2:
                remark = st.text_area("", value=st.session_state[remark_key], key=remark_key, height=75)
            with col3:
                remark_img = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"], key=file_key)

            if tested != st.session_state[tested_key] or remark != st.session_state[remark_key] or remark_img is not None:
                st.session_state[tested_key] = tested
                st.session_state[remark_key] = remark
                status = "Tested" if tested else "Not Tested"
                update_progress(tc_id, today, status, remark, user, remark_img)
                st.success(f"{tc_id} progress saved.")

# ---------- EDIT TEST CASES ----------
elif menu == "Edit Test Cases":
    st.title("📝 Edit / Add Test Cases")

    with st.expander("Add New Test Case"):
        def generate_next_id():
            if test_cases.empty:
                return "TC001"
            nums = [int(re.sub(r"\D", "", str(x))) for x in test_cases["Test Case ID"] if re.sub(r"\D", "", str(x)).isdigit()]
            return f"TC{max(nums) + 1:03d}" if nums else "TC001"

        new_id = generate_next_id()
        st.text_input("Test Case ID", value=new_id, disabled=True)
        page = st.text_input("Page/Field")
        module = st.text_input("Module")
        task = st.text_input("Task")
        steps = st.text_area("Steps")
        expected = st.text_area("Expected Result")
        image = st.file_uploader("Attach Image", type=["jpg", "jpeg", "png"])

        if st.button("Add Test Case"):
            image_filename = ""
            if image:
                safe_name = f"{new_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{sanitize_filename(image.name)}"
                with open(os.path.join(IMAGE_DIR, safe_name), "wb") as f:
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
            test_cases.loc[len(test_cases)] = new_row
            test_cases.to_excel(TEST_CASES_FILE, index=False, engine='openpyxl')
            st.success("Test case added!")

# ---------- DASHBOARD ----------
elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")

    if progress.empty:
        st.info("No test cases marked yet.")
    else:
        progress["Date"] = pd.to_datetime(progress["Date"], errors="coerce")
        today = datetime.date.today()
        week_tests = progress[progress["Date"] >= datetime.datetime.now() - datetime.timedelta(days=7)]

        st.metric("Tested Today", len(progress[progress["Date"].dt.date == today]))
        st.metric("Tested This Week", len(week_tests))
        st.metric("Total Logged", len(progress))

        tested = progress["Test Case ID"].nunique()
        total = test_cases["Test Case ID"].nunique()
        st.progress(tested / total if total else 0)

        merged = pd.merge(progress, test_cases, on="Test Case ID", how="left")
        st.dataframe(merged)

# ---------- REPORT ----------
elif menu == "Download Report":
    st.title("📄 Download Test Report")

    if progress.empty:
        st.warning("No report available.")
    else:
        merged = pd.merge(progress, test_cases, on="Test Case ID", how="left")
        report_file = os.path.join(PROGRESS_DIR, f"report_{user}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        merged.to_csv(report_file, index=False)
        st.success("Report ready!")

        with open(report_file, "rb") as f:
            st.download_button("📥 Download CSV", f, file_name=os.path.basename(report_file), mime="text/csv")
