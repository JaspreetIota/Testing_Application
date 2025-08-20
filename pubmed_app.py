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

# ---------- Ensure folders exist ----------
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# ---------- Initialize Files ----------
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result", "Image Filename"])
    df.to_excel(DATA_FILE, index=False, engine='openpyxl')

if not os.path.exists(PROGRESS_FILE):
    progress_df = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"])
    progress_df.to_csv(PROGRESS_FILE, index=False)

# ---------- Load Data ----------
test_cases = pd.read_excel(DATA_FILE, engine='openpyxl')
progress = pd.read_csv(PROGRESS_FILE)
# Ensure Date is datetime dtype
if not progress.empty:
    progress["Date"] = pd.to_datetime(progress["Date"], errors='coerce')

# ---------- Sidebar ----------
st.sidebar.title("🧪 Test Case Tracker")
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report"])

st.sidebar.markdown("---")
user = st.sidebar.text_input("Tester Name", value="Tester")

# ---------- Functions ----------
def generate_next_id():
    if test_cases.empty:
        return "TC001"
    else:
        ids = test_cases["Test Case ID"].dropna().tolist()
        numbers = []
        for id_ in ids:
            digits = ''.join(filter(str.isdigit, id_))
            if digits.isdigit():
                numbers.append(int(digits))
        next_num = max(numbers) + 1 if numbers else 1
        return f"TC{next_num:03d}"

def save_test_cases(df):
    df.to_excel(DATA_FILE, index=False, engine='openpyxl')

def save_progress(df):
    df.to_csv(PROGRESS_FILE, index=False)

# ---------- Run Tests ----------
if menu == "Run Tests":
    st.title("✅ Run Test Cases")

    view_mode = st.radio("Choose view mode:", ["Expanded View", "Table View"], horizontal=True)

    if view_mode == "Expanded View":
        if 'expanded_state' not in st.session_state:
            st.session_state.expanded_state = True
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Expand All"):
                st.session_state.expanded_state = True
        with col2:
            if st.button("Collapse All"):
                st.session_state.expanded_state = False

        for index, row in test_cases.iterrows():
            with st.expander(f"{row['Test Case ID']} - {row['Task']}", expanded=st.session_state.expanded_state):
                st.write(f"**Module:** {row['Module']}")
                st.write(f"**Page/Field:** {row['Page/Field']}")
                st.write(f"**Steps:** {row['Steps']}")
                st.write(f"**Expected Result:** {row['Expected Result']}")
                if pd.notna(row.get("Image Filename", None)) and row["Image Filename"]:
                    img_path = os.path.join(IMAGES_DIR, row["Image Filename"])
                    if os.path.exists(img_path):
                        st.image(img_path, caption="Test Case Image", use_column_width=True)

                key = f"{row['Test Case ID']}_tested"
                tested = st.checkbox("Mark as Tested", key=key)

                remark_key = f"{row['Test Case ID']}_remark"
                remark = st.text_area("Add remark (optional)", key=remark_key)

                # Allow uploading image with remark
                remark_img_key = f"{row['Test Case ID']}_remark_img"
                remark_img = st.file_uploader("Attach image with remark (optional)", type=["png","jpg","jpeg"], key=remark_img_key)

                if tested and not st.session_state.get(f"{key}_submitted", False):
                    global progress
                    # Save remark image if uploaded
                    remark_img_filename = ""
                    if remark_img is not None:
                        safe_filename = f"remark_{row['Test Case ID']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{remark_img.name}"
                        remark_img_path = os.path.join(IMAGES_DIR, safe_filename)
                        with open(remark_img_path, "wb") as f:
                            f.write(remark_img.getbuffer())
                        remark_img_filename = safe_filename

                    new_entry = {
                        "Test Case ID": row["Test Case ID"],
                        "Date": datetime.date.today(),
                        "Status": "Tested",
                        "Remarks": remark,
                        "User": user,
                        "Remark Image Filename": remark_img_filename
                    }
                    progress = pd.concat([progress, pd.DataFrame([new_entry])], ignore_index=True)
                    save_progress(progress)
                    st.success(f"{row['Test Case ID']} marked as tested!")
                    st.session_state[f"{key}_submitted"] = True

    else:  # Table view
        # Prepare display dataframe
        display_df = test_cases.copy()
        display_df = display_df.rename(columns={
            "Test Case ID": "ID",
            "Page/Field": "Page/Field",
            "Module": "Module",
            "Task": "Task",
            "Steps": "Steps",
            "Expected Result": "Expected Result"
        })
        st.dataframe(display_df)

        st.info("To mark test cases as tested or add remarks, switch to Expanded View.")

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
        image_file = st.file_uploader("Attach Image (optional)", type=["png", "jpg", "jpeg"])

        if st.button("Add Test Case"):
            global test_cases
            image_filename = ""
            if image_file is not None:
                safe_filename = f"testcase_{new_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.name}"
                image_path = os.path.join(IMAGES_DIR, safe_filename)
                with open(image_path, "wb") as f:
                    f.write(image_file.getbuffer())
                image_filename = safe_filename

            new_row = {
                "Test Case ID": new_id,
                "Page/Field": page,
                "Module": module,
                "Task": task,
                "Steps": steps,
                "Expected Result": expected,
                "Image Filename": image_filename
            }
            test_cases = pd.concat([test_cases, pd.DataFrame([new_row])], ignore_index=True)
            save_test_cases(test_cases)
            st.success(f"Test case {new_id} added!")

    st.markdown("---")

    # Bulk upload via Excel
    with st.expander("⬆️ Upload Test Cases via Excel"):
        uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
        if uploaded_file:
            try:
                df_uploaded = pd.read_excel(uploaded_file, engine='openpyxl')
                required_cols = ["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result"]
                missing_cols = [col for col in required_cols if col not in df_uploaded.columns]
                if missing_cols:
                    st.error(f"Uploaded file missing columns: {missing_cols}")
                else:
                    # Optionally handle Image Filename column if present
                    if "Image Filename" not in df_uploaded.columns:
                        df_uploaded["Image Filename"] = ""

                    # Append new cases (avoiding duplicate IDs)
                    existing_ids = set(test_cases["Test Case ID"].astype(str).tolist())
                    new_cases = df_uploaded[~df_uploaded["Test Case ID"].astype(str).isin(existing_ids)]

                    if not new_cases.empty:
                        test_cases = pd.concat([test_cases, new_cases], ignore_index=True)
                        save_test_cases(test_cases)
                        st.success(f"Uploaded {len(new_cases)} new test cases successfully!")
                    else:
                        st.info("No new test cases to add (all IDs already exist).")
            except Exception as e:
                st.error(f"Error reading uploaded file: {e}")

    st.subheader("✏️ Edit / Delete Existing Test Cases")

    if not test_cases.empty:
        edit_id = st.selectbox("Select Test Case ID", test_cases["Test Case ID"])

        row = test_cases[test_cases["Test Case ID"] == edit_id].iloc[0]

        new_page = st.text_input("Page/Field", row["Page/Field"])
        new_module = st.text_input("Module", row["Module"])
        new_task = st.text_input("Task", row["Task"])
        new_steps = st.text_area("Steps", row["Steps"])
        new_expected = st.text_area("Expected Result", row["Expected Result"])

        # Show current image if any
        if pd.notna(row.get("Image Filename", None)) and row["Image Filename"]:
            img_path = os.path.join(IMAGES_DIR, row["Image Filename"])
            if os.path.exists(img_path):
                st.image(img_path, caption="Attached Image", use_column_width=True)

        new_image_file = st.file_uploader("Replace Image (optional)", type=["png", "jpg", "jpeg"])

        if st.button("Save Changes"):
            global test_cases
            image_filename = row.get("Image Filename", "")
            if new_image_file is not None:
                safe_filename = f"testcase_{edit_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{new_image_file.name}"
                image_path = os.path.join(IMAGES_DIR, safe_filename)
                with open(image_path, "wb") as f:
                    f.write(new_image_file.getbuffer())
                image_filename = safe_filename
            test_cases.loc[test_cases["Test Case ID"] == edit_id, ["Page/Field", "Module", "Task", "Steps", "Expected Result", "Image Filename"]] = [new_page, new_module, new_task, new_steps, new_expected, image_filename]
            save_test_cases(test_cases)
            st.success("Changes saved!")

        if st.button("Delete Test Case"):
            test_cases = test_cases[test_cases["Test Case ID"] != edit_id]
            save_test_cases(test_cases)
            st.success(f"Test case {edit_id} deleted!")
    else:
        st.info("No test cases found.")

# ---------- Progress Dashboard ----------
elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")

    if progress.empty:
        st.info("No progress data available yet.")
    else:
        today = datetime.date.today()
        # Fix .dt accessor error by ensuring datetime dtype done at loading

        today_tests = progress[progress["Date"].dt.date == today]
        weekly_tests = progress[progress["Date"] >= pd.to_datetime(today - datetime.timedelta(days=7))]

        st.metric("Tested Today", len(today_tests))
        st.metric("Tested This Week", len(weekly_tests))
        st.metric("Total Tests Logged", len(progress))

        tested_cases = progress["Test Case ID"].nunique()
        total_cases = test_cases["Test Case ID"].nunique()

        if total_cases > 0:
            st.progress(tested_cases / total_cases)
        else:
            st.info("No test cases available to track progress.")

        st.subheader("🗂️ Test Case History")

        def format_row(row):
            # Show remark image if present as a link
            remark_img = row.get("Remark Image Filename", "")
            if remark_img and isinstance(remark_img, str):
                path = os.path.join(IMAGES_DIR, remark_img)
                if os.path.exists(path):
                    return f'{row["Remarks"]}  ![image](./{path})'
            return row["Remarks"]

        # Show progress dataframe with clickable images if possible
        display_progress = progress.copy()
        # Convert datetime to string for display
        display_progress["Date"] = display_progress["Date"].dt.strftime("%Y-%m-%d")

        st.dataframe(display_progress.sort_values(by="Date", ascending=False))

# ---------- Download Report ----------
elif menu == "Download Report":
    st.title("📄 Generate & Download Report")

    user_progress = progress if user.strip() == "" else progress[progress["User"] == user]

    if user_progress.empty:
        st.info("No test progress found.")
    else:
        report_date = datetime.date.today().strftime("%Y%m%d")
        safe_user = re.sub(r'\W+', '_', user.strip())
        filename = f"{REPORTS_DIR}/report_{safe_user}_{report_date}.csv"

        user_progress.to_csv(filename, index=False)

        st.success(f"Report generated for {user}")
        st.dataframe(user_progress)

        with open(filename, "rb") as file:
            st.download_button(
                label="📥 Download Report",
                data=file,
                file_name=os.path.basename(filename),
                mime="text/csv"
            )
