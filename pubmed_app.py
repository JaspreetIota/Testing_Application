import streamlit as st
import pandas as pd
import datetime
import os
import re

# ---------- File Paths ----------
DATA_FILE = "test_cases.xlsx"
PROGRESS_FILE = "progress.csv"
REPORTS_DIR = "reports"
IMAGES_DIR = "images"

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# ---------- Initialize Data ----------
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result", "Image Filename"])
    df.to_excel(DATA_FILE, index=False)

if not os.path.exists(PROGRESS_FILE):
    df = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"])
    df.to_csv(PROGRESS_FILE, index=False)

# ---------- Load Data ----------
test_cases = pd.read_excel(DATA_FILE)
progress = pd.read_csv(PROGRESS_FILE, parse_dates=["Date"], dayfirst=True)

# ---------- Session State Initialization ----------
if "tested" not in st.session_state:
    st.session_state.tested = {}
if "remarks" not in st.session_state:
    st.session_state.remarks = {}
if "remark_images" not in st.session_state:
    st.session_state.remark_images = {}

# ---------- Sidebar ----------
st.sidebar.title("🧪 Test Case Tracker")
user = st.sidebar.text_input("Tester Name").strip()
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report"])
st.sidebar.markdown("---")

# ---------- Helper Functions ----------
def generate_next_id():
    if test_cases.empty:
        return "TC001"
    existing_ids = test_cases["Test Case ID"].dropna().tolist()
    numbers = [int(re.sub(r"\D", "", x)) for x in existing_ids if re.sub(r"\D", "", x).isdigit()]
    next_num = max(numbers) + 1 if numbers else 1
    return f"TC{next_num:03d}"

def save_test_cases(df):
    df.to_excel(DATA_FILE, index=False)

def save_progress(df):
    df.to_csv(PROGRESS_FILE, index=False)

def auto_save_progress(tc_id, remark, remark_img_file):
    if not user:
        return
    today = datetime.date.today()

    remark_img_filename = ""
    if remark_img_file:
        safe_name = f"remark_{tc_id}_{user}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{remark_img_file.name}"
        img_path = os.path.join(IMAGES_DIR, safe_name)
        with open(img_path, "wb") as f:
            f.write(remark_img_file.getbuffer())
        remark_img_filename = safe_name

    new_entry = {
        "Test Case ID": tc_id,
        "Date": today,
        "Status": "Tested",
        "Remarks": remark,
        "User": user,
        "Remark Image Filename": remark_img_filename
    }

    match = (
        (progress["Test Case ID"] == tc_id) &
        (progress["Date"].dt.date == today) &
        (progress["User"] == user)
    )

    if progress[match].empty:
        progress.loc[len(progress)] = new_entry
    else:
        progress.loc[match, ["Remarks", "Remark Image Filename"]] = [remark, remark_img_filename]

    save_progress(progress)

# ---------- Run Tests ----------
if menu == "Run Tests":
    st.title("✅ Run Test Cases")

    view = st.radio("Choose View:", ["Expanded View", "Table View"], horizontal=True)

    if view == "Table View":
        st.dataframe(test_cases.drop(columns=["Image Filename"], errors="ignore"))
    else:
        for _, row in test_cases.iterrows():
            tc_id = row["Test Case ID"]
            with st.expander(f"{tc_id} - {row['Task']}", expanded=True):
                st.markdown(f"**Module:** {row['Module']}")
                st.markdown(f"**Page/Field:** {row['Page/Field']}")
                st.markdown(f"**Steps:** {row['Steps']}")
                st.markdown(f"**Expected Result:** {row['Expected Result']}")

                if pd.notna(row.get("Image Filename", "")):
                    img_path = os.path.join(IMAGES_DIR, row["Image Filename"])
                    if os.path.exists(img_path):
                        st.image(img_path, use_column_width=True)

                tested = st.checkbox("Mark as Tested", value=st.session_state.tested.get(tc_id, False), key=f"check_{tc_id}")
                st.session_state.tested[tc_id] = tested

                remark = st.text_area("Remark", value=st.session_state.remarks.get(tc_id, ""), key=f"remark_{tc_id}")
                st.session_state.remarks[tc_id] = remark

                remark_img = st.file_uploader("Attach image (optional)", type=["png", "jpg", "jpeg"], key=f"img_{tc_id}")
                st.session_state.remark_images[tc_id] = remark_img

                if tested:
                    auto_save_progress(tc_id, remark, remark_img)

# ---------- Edit Test Cases ----------
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
            test_cases.loc[len(test_cases)] = new_row
            save_test_cases(test_cases)
            st.success("Test case added.")

    st.markdown("---")
    st.subheader("✏️ Edit Existing Test Case")

    if not test_cases.empty:
        edit_id = st.selectbox("Select Test Case ID", test_cases["Test Case ID"])
        row = test_cases[test_cases["Test Case ID"] == edit_id].iloc[0]

        page = st.text_input("Page/Field", row["Page/Field"])
        module = st.text_input("Module", row["Module"])
        task = st.text_input("Task", row["Task"])
        steps = st.text_area("Steps", row["Steps"])
        expected = st.text_area("Expected Result", row["Expected Result"])
        new_image = st.file_uploader("Replace Image", type=["png", "jpg", "jpeg"])

        if st.button("Save Changes"):
            image_filename = row["Image Filename"]
            if new_image:
                safe_name = f"testcase_{edit_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{new_image.name}"
                with open(os.path.join(IMAGES_DIR, safe_name), "wb") as f:
                    f.write(new_image.getbuffer())
                image_filename = safe_name

            test_cases.loc[test_cases["Test Case ID"] == edit_id] = [
                edit_id, page, module, task, steps, expected, image_filename
            ]
            save_test_cases(test_cases)
            st.success("Changes saved.")

        if st.button("Delete Test Case"):
            test_cases.drop(test_cases[test_cases["Test Case ID"] == edit_id].index, inplace=True)
            save_test_cases(test_cases)
            st.success("Test case deleted.")

# ---------- Progress Dashboard ----------
elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")
    if progress.empty:
        st.info("No progress yet.")
    else:
        today = datetime.date.today()
        user_progress = progress[progress["User"] == user] if user else progress
        today_tests = user_progress[user_progress["Date"].dt.date == today]
        week_tests = user_progress[user_progress["Date"] >= pd.to_datetime(today - datetime.timedelta(days=7))]

        st.metric("Tested Today", len(today_tests))
        st.metric("Tested This Week", len(week_tests))
        st.metric("Total Logs", len(user_progress))

        tested_cases = user_progress["Test Case ID"].nunique()
        total_cases = test_cases["Test Case ID"].nunique()
        st.progress(tested_cases / total_cases if total_cases > 0 else 0)

        st.subheader("🗂️ Test Logs")
        st.dataframe(user_progress.sort_values(by="Date", ascending=False))

# ---------- Download Report ----------
elif menu == "Download Report":
    st.title("📥 Download Report")
    if not user:
        st.warning("Please enter a user name first.")
    else:
        filtered = progress[progress["User"] == user]
        if filtered.empty:
            st.info("No report data available.")
        else:
            date_str = datetime.date.today().strftime("%Y%m%d")
            filename = f"{REPORTS_DIR}/report_{user}_{date_str}.csv"
            filtered.to_csv(filename, index=False)

            st.success("Report generated.")
            with open(filename, "rb") as f:
                st.download_button("Download CSV", f, file_name=os.path.basename(filename), mime="text/csv")
