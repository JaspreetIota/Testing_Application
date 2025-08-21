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

# ---------- USER-BASED PROGRESS FILE ----------
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

# ---------- SAVE PROGRESS FUNCTION ----------
def save_progress():
    progress.to_csv(progress_file, index=False)

# ---------- RUN TESTS ----------
if menu == "Run Tests":
    st.title("✅ Run Test Cases")

    view_mode = st.radio("View Mode", ["Expanded View", "Table View"], horizontal=True)
    today = datetime.date.today()

    for _, row in test_cases.iterrows():
        tc_id = row['Test Case ID']
        with st.expander(f"{tc_id} - {row['Task']}", expanded=True if view_mode == "Expanded View" else False):
            st.markdown(f"**Module:** {row['Module']}")
            st.markdown(f"**Page/Field:** {row['Page/Field']}")
            st.markdown(f"**Steps:** {row['Steps']}")
            st.markdown(f"**Expected Result:** {row['Expected Result']}")

            if pd.notna(row.get("Image Filename", "")):
                img_path = os.path.join(IMAGE_DIR, row["Image Filename"])
                if os.path.exists(img_path):
                    st.image(img_path, caption="Attached Image")

            tested_key = f"{tc_id}_tested"
            remark_key = f"{tc_id}_remark"

            # Load state or initialize
            if tested_key not in st.session_state:
                st.session_state[tested_key] = False
            if remark_key not in st.session_state:
                st.session_state[remark_key] = ""
            if image_key not in st.session_state:
                st.session_state[image_key] = None

            tested = st.checkbox("Mark as Tested", key=tested_key)
            remark = st.text_area("Remarks", value=st.session_state[remark_key], key=remark_key)
            remark_img = st.file_uploader("Attach image (optional)", type=["jpg", "jpeg", "png"])

            # Auto Save
            if tested:
                already_logged = progress[(progress["Test Case ID"] == tc_id) & (progress["Date"].dt.date == today)].shape[0]
                if already_logged == 0:
                    remark_img_filename = ""
                    if remark_img:
                        safe_img_name = f"{tc_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{remark_img.name}"
                        image_path = os.path.join(IMAGE_DIR, safe_img_name)
                        with open(image_path, "wb") as f:
                            f.write(remark_img.getbuffer())
                        remark_img_filename = safe_img_name

                    new_entry = {
                        "Test Case ID": tc_id,
                        "Date": datetime.datetime.now(),
                        "Status": "Tested",
                        "Remarks": remark,
                        "User": user,
                        "Remark Image Filename": remark_img_filename
                    }
                    progress.loc[len(progress)] = new_entry
                    save_progress()
                    st.success("Auto-saved!")

    if view_mode == "Table View":
        st.dataframe(test_cases.drop(columns=["Image Filename"], errors="ignore"))

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
                safe_name = f"{new_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{image.name}"
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
        today = datetime.date.today()
        progress["Date"] = pd.to_datetime(progress["Date"], errors="coerce")
        today_tests = progress[progress["Date"].dt.date == today]
        week_tests = progress[progress["Date"] >= datetime.datetime.now() - datetime.timedelta(days=7)]

        st.metric("Tested Today", len(today_tests))
        st.metric("Tested This Week", len(week_tests))
        st.metric("Total Logged", len(progress))

        tested = progress["Test Case ID"].nunique()
        total = test_cases["Test Case ID"].nunique()
        st.progress(tested / total if total else 0)

        st.dataframe(progress)

# ---------- REPORT ----------
elif menu == "Download Report":
    st.title("📄 Download Test Report")

    if progress.empty:
        st.warning("No report available.")
    else:
        report_file = os.path.join(PROGRESS_DIR, f"report_{user}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        progress.to_csv(report_file, index=False)
        st.success("Report ready!")

        with open(report_file, "rb") as f:
            st.download_button("📥 Download CSV", f, file_name=os.path.basename(report_file), mime="text/csv")
