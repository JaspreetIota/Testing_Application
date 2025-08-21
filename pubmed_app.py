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
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Test Cases Table", "Progress Dashboard", "Download Report"])
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

# ---------- HELPER: SANITIZE FILENAME ----------
def sanitize_filename(filename):
    return re.sub(r'[^\w\-_\. ]', '_', filename)

# ---------- HELPER: GET PROGRESS ENTRY FOR USER AND DATE ----------
def get_progress_entry(tc_id, date, user):
    filtered = progress[
        (progress["Test Case ID"] == tc_id) &
        (progress["Date"].dt.date == date) &
        (progress["User"] == user)
    ]
    return filtered

# ---------- UPDATE OR ADD PROGRESS ENTRY ----------
def update_progress(tc_id, date, status, remarks, user, remark_img_file=None):
    filtered = get_progress_entry(tc_id, date, user)
    remark_img_filename = ""

    if not filtered.empty:
        idx = filtered.index[-1]
        # Handle image upload
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

    # Buttons to toggle views
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Expanded View"):
            st.session_state['view_mode'] = "Expanded"
    with col2:
        if st.button("Table View"):
            st.session_state['view_mode'] = "Table"

    view_mode = st.session_state.get('view_mode', "Expanded")

    if view_mode == "Expanded":
        today = datetime.date.today()
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

                tested_key = f"{tc_id}_tested"
                remark_key = f"{tc_id}_remark"

                # Initialize session state safely
                if tested_key not in st.session_state:
                    filtered = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (pd.to_datetime(progress["Date"], errors='coerce').dt.date == today) &
                        (progress["User"] == user)
                    ]
                    st.session_state[tested_key] = not filtered.empty and filtered.iloc[-1]["Status"] == "Tested"
                if remark_key not in st.session_state:
                    filtered = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (pd.to_datetime(progress["Date"], errors='coerce').dt.date == today) &
                        (progress["User"] == user)
                    ]
                    if not filtered.empty:
                        st.session_state[remark_key] = filtered.iloc[-1]["Remarks"] if pd.notna(filtered.iloc[-1]["Remarks"]) else ""
                    else:
                        st.session_state[remark_key] = ""

                tested = st.checkbox("Mark as Tested", key=tested_key)
                remark = st.text_area("Remarks", value=st.session_state[remark_key] or "", key=remark_key)
                remark_img = st.file_uploader("Attach image (optional)", type=["jpg", "jpeg", "png"], key=f"{tc_id}_file")

                # Auto Save Logic
                if tested:
                    update_progress(tc_id, today, "Tested", remark, user, remark_img)
                    st.success("Auto-saved!")

                elif tested_key in st.session_state and not tested:
                    # If unchecked, remove or mark as Not Tested
                    # For simplicity, mark as Not Tested with empty remarks
                    update_progress(tc_id, today, "Not Tested", "", user)
                    st.info(f"Marked {tc_id} as Not Tested.")

    elif view_mode == "Table":
        st.info("Edit the test cases directly below. After editing, click 'Save Edits' to update.")
        edited_df = st.experimental_data_editor(test_cases, num_rows="dynamic")
        if st.button("Save Edits"):
            edited_df.to_excel(TEST_CASES_FILE, index=False, engine='openpyxl')
            st.success("Test cases updated!")
            # Reload updated test_cases
            test_cases = pd.read_excel(TEST_CASES_FILE, engine='openpyxl')

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

# ---------- NEW VIEW: TEST CASES TABLE WITH PROGRESS ----------
elif menu == "Test Cases Table":
    st.title("🧪 Test Cases Table with Marking")

    today = datetime.date.today()

    # Merge test_cases with progress for today's user progress
    today_progress = progress[
        (progress["Date"].dt.date == today) &
        (progress["User"] == user)
    ].copy()

    # Use dict for quick lookup of progress by Test Case ID
    progress_map = {}
    for _, row in today_progress.iterrows():
        progress_map[row["Test Case ID"]] = row

    # Prepare lists for updated progress (to batch save later)
    updated_entries = []

    st.write("Mark test cases as tested, add remarks and upload images below. Changes auto-save.")

    for idx, row in test_cases.iterrows():
        tc_id = row["Test Case ID"]
        st.markdown(f"---\n**{tc_id} - {row['Task']}**")

        # Get existing progress info if available
        prog_entry = progress_map.get(tc_id, None)
        tested_key = f"{tc_id}_table_tested"
        remark_key = f"{tc_id}_table_remark"
        file_key = f"{tc_id}_table_file"

        # Initialize session state if not exist
        if tested_key not in st.session_state:
            st.session_state[tested_key] = (prog_entry is not None and prog_entry["Status"] == "Tested")
        if remark_key not in st.session_state:
            st.session_state[remark_key] = prog_entry["Remarks"] if (prog_entry is not None and pd.notna(prog_entry["Remarks"])) else ""
        if file_key not in st.session_state:
            st.session_state[file_key] = None

        # UI elements
        col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
        with col1:
            tested = st.checkbox("", key=tested_key)
        with col2:
            remark = st.text_area("", value=st.session_state[remark_key], key=remark_key, height=75)
        with col3:
            remark_img = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"], key=file_key)

        # When any input changes, update progress immediately
        if tested != st.session_state[tested_key] or remark != st.session_state[remark_key] or remark_img is not None:
            st.session_state[tested_key] = tested
            st.session_state[remark_key] = remark

            # Save progress immediately
            if tested:
                update_progress(tc_id, today, "Tested", remark, user, remark_img)
                st.success(f"{tc_id} progress saved.")
            else:
                update_progress(tc_id, today, "Not Tested", "", user)
                st.info(f"{tc_id} marked as Not Tested.")

# ---------- DASHBOARD ----------
elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")

    if progress.empty:
        st.info("No test cases marked yet.")
    else:
        today = datetime.date.today()
        progress["Date"] = pd.to_datetime(progress["Date"], errors="coerce")
        today_tests = progress[progress["Date"].dt.date == today].copy()
        week_tests = progress[progress["Date"] >= datetime.datetime.now() - datetime.timedelta(days=7)].copy()

        st.metric("Tested Today", len(today_tests))
        st.metric("Tested This Week", len(week_tests))
        st.metric("Total Logged", len(progress))

        tested = progress["Test Case ID"].nunique()
        total = test_cases["Test Case ID"].nunique()
        st.progress(tested / total if total else 0)

        # Join progress with test_cases info
        merged = progress.merge(test_cases, on="Test Case ID", how="left")

        # Show important columns
        cols_to_show = ["Test Case ID", "Date", "Status", "User", "Remarks", "Remark Image Filename",
                        "Page/Field", "Module", "Task", "Steps", "Expected Result"]
        merged_display = merged[cols_to_show].copy()

        # Format Date nicely
        merged_display["Date"] = merged_display["Date"].dt.strftime("%Y-%m-%d %H:%M:%S")

        st.dataframe(merged_display)

# ---------- REPORT ----------
elif menu == "Download Report":
    st.title("📄 Download Test Report")

    if progress.empty:
        st.warning("No report available.")
    else:
        # Merge with test cases for full details
        merged = progress.merge(test_cases, on="Test Case ID", how="left")

        cols_to_export = ["Test Case ID", "Date", "Status", "User", "Remarks", "Remark Image Filename",
                          "Page/Field", "Module", "Task", "Steps", "Expected Result"]

        report_df = merged[cols_to_export].copy()
        report_df["Date"] = pd.to_datetime(report_df["Date"], errors='coerce').dt.strftime("%Y-%m-%d %H:%M:%S")

        report_file = os.path.join(PROGRESS_DIR, f"report_{user}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        report_df.to_csv(report_file, index=False)
        st.success("Report ready!")

        with open(report_file, "rb") as f:
            st.download_button("📥 Download CSV", f, file_name=os.path.basename(report_file), mime="text/csv")
