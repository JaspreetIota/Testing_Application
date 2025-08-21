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
    if "Date" in progress.columns:
        progress["Date"] = pd.to_datetime(progress["Date"], errors='coerce')
    else:
        progress["Date"] = pd.NaT
    if not progress.empty:
        # keep only relevant columns if any unexpected columns present
        expected_cols = ["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"]
        progress = progress.reindex(columns=expected_cols, fill_value=None)
else:
    progress = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"])

# ---------- SAVE PROGRESS FUNCTION ----------
def save_progress():
    progress.to_csv(progress_file, index=False)

# ---------- CLEAR TODAY'S PROGRESS FUNCTION ----------
def clear_todays_progress():
    global progress
    today = datetime.date.today()
    before_len = len(progress)
    # Remove all progress for user for today's date
    progress = progress[~(
        (progress["User"] == user) & 
        (progress["Date"].notnull()) &
        (progress["Date"].dt.date == today)
    )].copy()
    save_progress()
    # Clear session state keys related to today and this user
    keys_to_clear = [key for key in st.session_state.keys() if key.endswith('_tested') or key.endswith('_remark') or key.endswith('_file')]
    for key in keys_to_clear:
        del st.session_state[key]
    st.success(f"Cleared today's progress. Removed {before_len - len(progress)} entries.")

# ---------- RUN TESTS ----------
if menu == "Run Tests":
    st.title("✅ Run Test Cases")

    col1, col2, col3 = st.columns([1,1,2])
    with col1:
        if st.button("Expanded View"):
            st.session_state['view_mode'] = "Expanded"
    with col2:
        if st.button("Alternate Table View"):
            st.session_state['view_mode'] = "AltTable"
    with col3:
        if st.button("Clear Today's Progress"):
            clear_todays_progress()

    view_mode = st.session_state.get('view_mode', "Expanded")

    today = datetime.date.today()

    if view_mode == "Expanded":
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
                file_key = f"{tc_id}_file"

                # Initialize session state safely with today's progress
                if tested_key not in st.session_state:
                    filtered = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (progress["Date"].notnull()) &
                        (progress["Date"].dt.date == today)
                    ]
                    st.session_state[tested_key] = not filtered.empty and filtered.iloc[-1]["Status"] == "Tested"
                if remark_key not in st.session_state:
                    filtered = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (progress["Date"].notnull()) &
                        (progress["Date"].dt.date == today)
                    ]
                    if not filtered.empty:
                        st.session_state[remark_key] = filtered.iloc[-1]["Remarks"] if pd.notna(filtered.iloc[-1]["Remarks"]) else ""
                    else:
                        st.session_state[remark_key] = ""
                if file_key not in st.session_state:
                    # No need to initialize, uploader is empty by default
                    st.session_state[file_key] = None

                tested = st.checkbox("Mark as Tested", key=tested_key)
                remark = st.text_area("Remarks", value=st.session_state[remark_key] or "", key=remark_key)
                remark_img = st.file_uploader("Attach image (optional)", type=["jpg", "jpeg", "png"], key=file_key)

                # Auto Save Logic
                if tested:
                    filtered = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (progress["Date"].notnull()) &
                        (progress["Date"].dt.date == today)
                    ].copy()

                    if filtered.empty:
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
                        st.success(f"Auto-saved progress for {tc_id}")
                    else:
                        idx = filtered.index[-1]
                        remark_img_filename = progress.at[idx, "Remark Image Filename"]
                        if remark_img:
                            safe_img_name = f"{tc_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{remark_img.name}"
                            image_path = os.path.join(IMAGE_DIR, safe_img_name)
                            with open(image_path, "wb") as f:
                                f.write(remark_img.getbuffer())
                            remark_img_filename = safe_img_name
                        progress.at[idx, "Remarks"] = remark
                        progress.at[idx, "Remark Image Filename"] = remark_img_filename
                        progress.at[idx, "Date"] = datetime.datetime.now()
                        progress.at[idx, "Status"] = "Tested"
                        progress.at[idx, "User"] = user
                        save_progress()
                        st.success(f"Updated progress for {tc_id}")
                else:
                    # If unchecked, remove today's tested progress for this test case
                    idxs = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (progress["Date"].notnull()) &
                        (progress["Date"].dt.date == today)
                    ].index
                    if len(idxs) > 0:
                        progress.drop(idxs, inplace=True)
                        save_progress()
                        st.info(f"Removed progress for {tc_id}")

    elif view_mode == "AltTable":
        st.markdown("📋 **Alternate Table View for Running Tests**")

        # Build list of dict rows for the table
        rows = []
        for _, row in test_cases.iterrows():
            tc_id = row['Test Case ID']

            tested_key = f"{tc_id}_tested"
            remark_key = f"{tc_id}_remark"
            file_key = f"{tc_id}_file"

            if tested_key not in st.session_state:
                filtered = progress[
                    (progress["Test Case ID"] == tc_id) &
                    (progress["Date"].notnull()) &
                    (progress["Date"].dt.date == today)
                ]
                st.session_state[tested_key] = not filtered.empty and filtered.iloc[-1]["Status"] == "Tested"

            if remark_key not in st.session_state:
                filtered = progress[
                    (progress["Test Case ID"] == tc_id) &
                    (progress["Date"].notnull()) &
                    (progress["Date"].dt.date == today)
                ]
                if not filtered.empty:
                    st.session_state[remark_key] = filtered.iloc[-1]["Remarks"] if pd.notna(filtered.iloc[-1]["Remarks"]) else ""
                else:
                    st.session_state[remark_key] = ""

            if file_key not in st.session_state:
                st.session_state[file_key] = None

            rows.append({
                "Test Case ID": tc_id,
                "Task": row['Task'],
                "Tested": st.checkbox("", key=tested_key),
                "Remarks": st.text_area("", key=remark_key, placeholder="Remarks"),
                "Upload": st.file_uploader("", type=["jpg", "jpeg", "png"], key=file_key, label_visibility="collapsed")
            })

        # Because Streamlit components (checkbox, text_area, file_uploader) inside loops don't show in a neat table,
        # We need to display row-wise as columns

        for i, row in enumerate(test_cases.itertuples()):
            tc_id = row._1  # Test Case ID
            st.markdown(f"### {tc_id}: {row.Task}")

            col_tested, col_remarks, col_upload = st.columns([1, 3, 3])
            with col_tested:
                tested_key = f"{tc_id}_tested"
                tested = st.checkbox("Tested", key=tested_key)
            with col_remarks:
                remark_key = f"{tc_id}_remark"
                remark = st.text_area("Remarks", key=remark_key)
            with col_upload:
                file_key = f"{tc_id}_file"
                remark_img = st.file_uploader("Upload image", type=["jpg", "jpeg", "png"], key=file_key)

            # Save on interaction
            if tested:
                filtered = progress[
                    (progress["Test Case ID"] == tc_id) &
                    (progress["Date"].notnull()) &
                    (progress["Date"].dt.date == today)
                ].copy()
                if filtered.empty:
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
                    st.success(f"Auto-saved progress for {tc_id}")
                else:
                    idx = filtered.index[-1]
                    remark_img_filename = progress.at[idx, "Remark Image Filename"]
                    if remark_img:
                        safe_img_name = f"{tc_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{remark_img.name}"
                        image_path = os.path.join(IMAGE_DIR, safe_img_name)
                        with open(image_path, "wb") as f:
                            f.write(remark_img.getbuffer())
                        remark_img_filename = safe_img_name
                    progress.at[idx, "Remarks"] = remark
                    progress.at[idx, "Remark Image Filename"] = remark_img_filename
                    progress.at[idx, "Date"] = datetime.datetime.now()
                    progress.at[idx, "Status"] = "Tested"
                    progress.at[idx, "User"] = user
                    save_progress()
                    st.success(f"Updated progress for {tc_id}")
            else:
                # If unchecked, remove today's tested progress for this test case
                idxs = progress[
                    (progress["Test Case ID"] == tc_id) &
                    (progress["Date"].notnull()) &
                    (progress["Date"].dt.date == today)
                ].index
                if len(idxs) > 0:
                    progress.drop(idxs, inplace=True)
                    save_progress()
                    st.info(f"Removed progress for {tc_id}")

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

    # Also add Edit table view
    st.markdown("### Edit Existing Test Cases")
    edited_df = st.experimental_data_editor(test_cases, num_rows="dynamic")
    if st.button("Save Edits"):
        edited_df.to_excel(TEST_CASES_FILE, index=False, engine='openpyxl')
        st.success("Test cases updated!")
        test_cases = pd.read_excel(TEST_CASES_FILE, engine='openpyxl')

# ---------- DASHBOARD ----------
elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")
    if progress.empty or len(progress[progress["Status"] == "Tested"]) == 0:
        st.info("No test cases marked as tested yet.")
    else:
        today = datetime.date.today()
        progress["Date"] = pd.to_datetime(progress["Date"], errors="coerce")

        today_tests = progress[(progress["Date"].notnull()) & (progress["Date"].dt.date == today) & (progress["Status"] == "Tested")].copy()
        week_tests = progress[(progress["Date"] >= datetime.datetime.now() - datetime.timedelta(days=7)) & (progress["Status"] == "Tested")].copy()

        st.metric("Tested Today", len(today_tests))
        st.metric("Tested This Week", len(week_tests))
        st.metric("Total Logged", len(progress[progress["Status"] == "Tested"]))

        tested = progress[progress["Status"] == "Tested"]["Test Case ID"].nunique()
        total = test_cases["Test Case ID"].nunique()
        st.progress(tested / total if total else 0)

        st.dataframe(progress[progress["Status"] == "Tested"])

# ---------- REPORT ----------
elif menu == "Download Report":
    st.title("📄 Download Test Report")
    if progress.empty or len(progress[progress["Status"] == "Tested"]) == 0:
        st.warning("No report available.")
    else:
        report_file = os.path.join(PROGRESS_DIR, f"report_{user}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        progress[progress["Status"] == "Tested"].to_csv(report_file, index=False)
        st.success("Report ready!")
        with open(report_file, "rb") as f:
            st.download_button("📥 Download CSV", f, file_name=os.path.basename(report_file), mime="text/csv")
