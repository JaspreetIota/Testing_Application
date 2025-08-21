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
def load_progress():
    if os.path.exists(progress_file) and os.path.getsize(progress_file) > 0:
        df = pd.read_csv(progress_file)
        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        return df
    else:
        return pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"])

progress = load_progress()

# ---------- SAVE PROGRESS FUNCTION ----------
def save_progress():
    progress.to_csv(progress_file, index=False)

# ---------- RESET PROGRESS FUNCTION ----------
def reset_progress_for_user():
    if os.path.exists(progress_file):
        os.remove(progress_file)
    global progress
    progress = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"])
    save_progress()
    # Clear session states related to test cases
    for key in list(st.session_state.keys()):
        if key.endswith("_tested") or key.endswith("_remark") or key.endswith("_file"):
            del st.session_state[key]

# ---------- RUN TESTS ----------
if menu == "Run Tests":
    st.title("✅ Run Test Cases")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Expanded View"):
            st.session_state['view_mode'] = "Expanded"
    with col2:
        if st.button("Edit Test Cases"):
            # Redirect user to the Edit Test Cases page
            st.experimental_rerun()  # This will reload with menu selection changed (handled in sidebar)
    with col3:
        if st.button("Table Test View"):
            st.session_state['view_mode'] = "TableTest"

    st.markdown("---")

    view_mode = st.session_state.get('view_mode', "Expanded")

    today = datetime.date.today()

    if st.button("Reset Progress for Today"):
        reset_progress_for_user()
        st.success("Progress reset for this user.")
        st.experimental_rerun()

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

                # Restore from today's progress if any
                if tested_key not in st.session_state:
                    filtered = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (progress["Date"].dt.date == today)
                    ]
                    st.session_state[tested_key] = not filtered.empty and filtered.iloc[-1]["Status"] == "Tested"
                if remark_key not in st.session_state:
                    filtered = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (progress["Date"].dt.date == today)
                    ]
                    if not filtered.empty:
                        st.session_state[remark_key] = filtered.iloc[-1]["Remarks"] if pd.notna(filtered.iloc[-1]["Remarks"]) else ""
                    else:
                        st.session_state[remark_key] = ""

                tested = st.checkbox("Mark as Tested", key=tested_key)
                remark = st.text_area("Remarks", value=st.session_state[remark_key] or "", key=remark_key)
                remark_img = st.file_uploader("Attach image (optional)", type=["jpg", "jpeg", "png"], key=f"{tc_id}_file")

                if tested:
                    # Save or update progress for today & this test case
                    filtered = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (progress["Date"].dt.date == today)
                    ].copy()

                    remark_img_filename = ""
                    if not filtered.empty:
                        idx = filtered.index[-1]
                        remark_img_filename = progress.at[idx, "Remark Image Filename"]
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

                    if filtered.empty:
                        progress.loc[len(progress)] = new_entry
                    else:
                        progress.loc[idx] = new_entry

                    save_progress()
                    st.success(f"{tc_id} saved.")

    elif view_mode == "TableTest":
        # Create a dataframe that includes test cases + today's progress info for user
        # Prepare columns: Mark as Tested, Remarks, Attach Image (file uploader)
        merged_df = test_cases.copy()

        # Add columns for today's progress if exists
        today_progress = progress[
            (progress["Date"].dt.date == today) &
            (progress["User"] == user) &
            (progress["Status"] == "Tested")
        ]

        # Map progress info to test_cases
        merged_df["Tested"] = False
        merged_df["Remarks"] = ""
        merged_df["Remark Image Filename"] = ""

        for i, row in merged_df.iterrows():
            tc_id = row["Test Case ID"]
            filtered = today_progress[today_progress["Test Case ID"] == tc_id]
            if not filtered.empty:
                merged_df.at[i, "Tested"] = True
                merged_df.at[i, "Remarks"] = filtered.iloc[-1]["Remarks"] if pd.notna(filtered.iloc[-1]["Remarks"]) else ""
                merged_df.at[i, "Remark Image Filename"] = filtered.iloc[-1]["Remark Image Filename"] if pd.notna(filtered.iloc[-1]["Remark Image Filename"]) else ""

        # We will now display editable table with Tested (bool), Remarks (string), and upload image file column.
        st.info("You can mark test cases as tested, add remarks and upload images directly here. Changes auto-save.")

        edited_rows = []
        for idx, row in merged_df.iterrows():
            st.write(f"**{row['Test Case ID']} - {row['Task']}**")
            col1, col2, col3, col4 = st.columns([1, 3, 3, 3])
            tested_key = f"{row['Test Case ID']}_table_tested"
            remark_key = f"{row['Test Case ID']}_table_remark"
            file_key = f"{row['Test Case ID']}_table_file"

            # Initialize session state for these keys
            if tested_key not in st.session_state:
                st.session_state[tested_key] = row["Tested"]
            if remark_key not in st.session_state:
                st.session_state[remark_key] = row["Remarks"]

            with col1:
                tested = st.checkbox("Tested", value=st.session_state[tested_key], key=tested_key)
            with col2:
                remark = st.text_area("Remarks", value=st.session_state[remark_key], key=remark_key)
            with col3:
                uploaded_file = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"], key=file_key)

            # If tested changed or remark changed or file uploaded, save progress
            if tested != st.session_state[tested_key] or remark != st.session_state[remark_key] or uploaded_file is not None:
                st.session_state[tested_key] = tested
                st.session_state[remark_key] = remark

                # Save or update progress
                filtered = progress[
                    (progress["Test Case ID"] == row["Test Case ID"]) &
                    (progress["Date"].dt.date == today) &
                    (progress["User"] == user)
                ]

                remark_img_filename = ""
                if not filtered.empty:
                    idx_prog = filtered.index[-1]
                    remark_img_filename = progress.at[idx_prog, "Remark Image Filename"]
                else:
                    idx_prog = None

                if uploaded_file:
                    safe_img_name = f"{row['Test Case ID']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{uploaded_file.name}"
                    image_path = os.path.join(IMAGE_DIR, safe_img_name)
                    with open(image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    remark_img_filename = safe_img_name

                new_entry = {
                    "Test Case ID": row["Test Case ID"],
                    "Date": datetime.datetime.now(),
                    "Status": "Tested" if tested else "Not Tested",
                    "Remarks": remark,
                    "User": user,
                    "Remark Image Filename": remark_img_filename
                }

                if idx_prog is None:
                    progress.loc[len(progress)] = new_entry
                else:
                    progress.loc[idx_prog] = new_entry

                save_progress()
                st.success(f"{row['Test Case ID']} progress saved.")

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

        st.markdown("---")
        st.info("Edit existing test cases below and click 'Save Edits'.")

        edited_df = st.experimental_data_editor(test_cases, num_rows="dynamic")
        if st.button("Save Edits"):
            edited_df.to_excel(TEST_CASES_FILE, index=False, engine='openpyxl')
            st.success("Test cases updated!")
            # Reload after save
            test_cases = pd.read_excel(TEST_CASES_FILE, engine='openpyxl')

    elif menu == "Progress Dashboard":
        st.title("📊 Progress Dashboard")
        if progress.empty:
            st.info("No test cases marked yet.")
        else:
            # Filter only 'Tested' status rows
            tested_progress = progress[progress["Status"] == "Tested"]

            today = datetime.date.today()
            today_tests = tested_progress[tested_progress["Date"].dt.date == today].copy()
            week_tests = tested_progress[tested_progress["Date"] >= (datetime.datetime.now() - datetime.timedelta(days=7))].copy()

            st.metric("Tested Today", len(today_tests))
            st.metric("Tested This Week", len(week_tests))
            st.metric("Total Logged", len(tested_progress))

            tested = tested_progress["Test Case ID"].nunique()
            total = test_cases["Test Case ID"].nunique()
            st.progress(tested / total if total else 0)

            st.dataframe(tested_progress)

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
