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
# Convert Date column to datetime if it exists and not empty
if "Date" in progress.columns:
    progress["Date"] = pd.to_datetime(progress["Date"], errors='coerce')

# ---------- Sidebar ----------
st.sidebar.title("🧪 Test Case Tracker")
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report"])

st.sidebar.markdown("---")
user = st.sidebar.text_input("Tester Name", value="Tester")

# ---------- Helper: Generate Next Test Case ID ----------
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

# ---------- Run Tests ----------
if menu == "Run Tests":
    st.title("✅ Run Test Cases")
    
    # Allow user to switch view mode: expanded or table
    view_mode = st.radio("View Mode", ["Expanded View", "Table View"], horizontal=True)
    
    if view_mode == "Expanded View":
        # Button to expand/collapse all test cases
        if "all_expanded" not in st.session_state:
            st.session_state.all_expanded = True
        
        expand_collapse = st.button("Toggle Expand/Collapse All")
        if expand_collapse:
            st.session_state.all_expanded = not st.session_state.all_expanded
        
        for idx, row in test_cases.iterrows():
            with st.expander(f"{row['Test Case ID']} - {row['Task']}", expanded=st.session_state.all_expanded):
                st.markdown(f"**Module**: {row['Module']}")
                st.markdown(f"**Page/Field**: {row['Page/Field']}")
                st.markdown(f"**Steps**:\n{row['Steps']}")
                st.markdown(f"**Expected Result**:\n{row['Expected Result']}")
                
                # Show test case image if exists
                img_file = row.get("Image Filename")
                if pd.notna(img_file) and os.path.exists(os.path.join(IMAGES_DIR, img_file)):
                    st.image(os.path.join(IMAGES_DIR, img_file), caption="Test Case Image", use_column_width=True)
                
                # Checkbox to mark tested
                key = f"{row['Test Case ID']}_tested"
                tested = st.checkbox("Mark as Tested", key=key)

                # Remark input and image upload for remarks
                remark_key = f"{row['Test Case ID']}_remark"
                remark = st.text_area("Add remark (optional)", key=remark_key)

                remark_img_key = f"{row['Test Case ID']}_remark_img"
                remark_img = st.file_uploader("Upload Remark Image (optional)", type=["png", "jpg", "jpeg"], key=remark_img_key)

                if tested and not st.session_state.get(f"{key}_submitted", False):
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
                    global progress
                    progress = pd.concat([progress, pd.DataFrame([new_entry])], ignore_index=True)
                    progress.to_csv(PROGRESS_FILE, index=False)
                    st.success(f"{row['Test Case ID']} marked as tested!")
                    st.session_state[f"{key}_submitted"] = True

    else:  # Table View
        st.subheader("Test Cases Table")
        # Add a column for "Mark as Tested" checkbox and remarks inputs
        # For table view, show as editable dataframe or use form per row (limited in Streamlit)
        
        # We'll create a simple table with current progress status
        merged = pd.merge(test_cases, progress.groupby("Test Case ID").last().reset_index()[["Test Case ID", "Status", "Remarks", "User"]], on="Test Case ID", how="left")
        merged = merged.fillna({"Status": "Not Tested", "Remarks": "", "User": ""})
        st.dataframe(merged[["Test Case ID", "Page/Field", "Module", "Task", "Status", "User", "Remarks"]])

        st.info("In table view, marking test cases as tested with remarks is not supported. Please use Expanded View to mark tests.")

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

        # Image upload for test case
        uploaded_img = st.file_uploader("Upload Test Case Image (optional)", type=["png", "jpg", "jpeg"])

        if st.button("Add Test Case"):
            img_filename = ""
            if uploaded_img is not None:
                safe_img_name = f"tc_{new_id}_{uploaded_img.name}"
                img_path = os.path.join(IMAGES_DIR, safe_img_name)
                with open(img_path, "wb") as f:
                    f.write(uploaded_img.getbuffer())
                img_filename = safe_img_name

            new_row = {
                "Test Case ID": new_id,
                "Page/Field": page,
                "Module": module,
                "Task": task,
                "Steps": steps,
                "Expected Result": expected,
                "Image Filename": img_filename
            }
            global test_cases
            test_cases = pd.concat([test_cases, pd.DataFrame([new_row])], ignore_index=True)
            test_cases.to_excel(DATA_FILE, index=False, engine='openpyxl')
            st.success(f"Test case {new_id} added!")

    # Bulk upload via Excel
    with st.expander("📁 Upload Test Cases via Excel"):
        uploaded_file = st.file_uploader("Upload Excel file (.xlsx) with columns: Test Case ID (optional), Page/Field, Module, Task, Steps, Expected Result", type=["xlsx"])
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_excel(uploaded_file, engine='openpyxl')
                # Auto-generate IDs if missing
                if "Test Case ID" not in uploaded_df.columns or uploaded_df["Test Case ID"].isnull().all():
                    # Generate IDs for rows missing ID or all missing
                    start_num = 1
                    if not test_cases.empty:
                        existing_ids = test_cases["Test Case ID"].dropna().tolist()
                        existing_nums = [int(''.join(filter(str.isdigit, x))) for x in existing_ids if ''.join(filter(str.isdigit, x)).isdigit()]
                        if existing_nums:
                            start_num = max(existing_nums) + 1

                    new_ids = []
                    for i in range(len(uploaded_df)):
                        new_ids.append(f"TC{start_num+i:03d}")
                    uploaded_df["Test Case ID"] = new_ids

                # Remove duplicates based on Test Case ID
                existing_ids_set = set(test_cases["Test Case ID"].tolist())
                uploaded_df = uploaded_df[~uploaded_df["Test Case ID"].isin(existing_ids_set)]

                # Append and save
                test_cases = pd.concat([test_cases, uploaded_df], ignore_index=True)
                test_cases.to_excel(DATA_FILE, index=False, engine='openpyxl')
                st.success(f"Uploaded {len(uploaded_df)} new test cases!")
            except Exception as e:
                st.error(f"Error reading Excel file: {e}")

    st.markdown("---")
    st.subheader("✏️ Edit / Delete Existing Test Cases")

    if not test_cases.empty:
        edit_id = st.selectbox("Select Test Case ID", test_cases["Test Case ID"])
        row = test_cases[test_cases["Test Case ID"] == edit_id].iloc[0]

        new_page = st.text_input("Page/Field", row["Page/Field"])
        new_module = st.text_input("Module", row["Module"])
        new_task = st.text_input("Task", row["Task"])
        new_steps = st.text_area("Steps", row["Steps"])
        new_expected = st.text_area("Expected Result", row["Expected Result"])

        # Show existing image if available
        if pd.notna(row.get("Image Filename")) and os.path.exists(os.path.join(IMAGES_DIR, row["Image Filename"])):
            st.image(os.path.join(IMAGES_DIR, row["Image Filename"]), caption="Current Test Case Image", use_column_width=True)
        # Upload new image
        new_uploaded_img = st.file_uploader("Replace Test Case Image (optional)", type=["png", "jpg", "jpeg"])

        if st.button("Save Changes"):
            img_filename = row.get("Image Filename", "")
            if new_uploaded_img is not None:
                # Save new image
                safe_img_name = f"tc_{edit_id}_{new_uploaded_img.name}"
                img_path = os.path.join(IMAGES_DIR, safe_img_name)
                with open(img_path, "wb") as f:
                    f.write(new_uploaded_img.getbuffer())
                img_filename = safe_img_name

            test_cases.loc[test_cases["Test Case ID"] == edit_id, ["Page/Field", "Module", "Task", "Steps", "Expected Result", "Image Filename"]] = [new_page, new_module, new_task, new_steps, new_expected, img_filename]
            test_cases.to_excel(DATA_FILE, index=False, engine='openpyxl')
            st.success("Changes saved!")

        if st.button("Delete Test Case"):
            # Remove associated image file
            img_filename = row.get("Image Filename")
            if pd.notna(img_filename):
                try:
                    os.remove(os.path.join(IMAGES_DIR, img_filename))
                except:
                    pass

            # Remove test case
            test_cases = test_cases[test_cases["Test Case ID"] != edit_id]
            test_cases.to_excel(DATA_FILE, index=False, engine='openpyxl')

            # Remove progress entries for this test case
            global progress
            progress = progress[progress["Test Case ID"] != edit_id]
            progress.to_csv(PROGRESS_FILE, index=False)
            st.success(f"Test case {edit_id} deleted.")
    else:
        st.info("No test cases found.")

# ---------- Progress Dashboard ----------
elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")

    today = datetime.date.today()
    if not progress.empty and "Date" in progress.columns:
        today_tests = progress[progress["Date"].dt.date == today]
        weekly_tests = progress[progress["Date"] >= pd.to_datetime(today - datetime.timedelta(days=7))]
    else:
        today_tests = pd.DataFrame()
        weekly_tests = pd.DataFrame()

    st.metric("Tested Today", len(today_tests))
    st.metric("Tested This Week", len(weekly_tests))
    st.metric("Total Tests Logged", len(progress))

    tested_cases = progress["Test Case ID"].nunique() if not progress.empty else 0
    total_cases = test_cases["Test Case ID"].nunique() if not test_cases.empty else 0

    if total_cases > 0:
        st.progress(tested_cases / total_cases)
    else:
        st.info("No test cases available to track progress.")

    st.subheader("🗂️ Test Case History")

    # Show images uploaded in remarks as thumbnails with link
    def format_remarks(row):
        text = row["Remarks"] if pd.notna(row["Remarks"]) else ""
        img_file = row.get("Remark Image Filename", "")
        if pd.notna(img_file) and img_file and os.path.exists(os.path.join(IMAGES_DIR, img_file)):
            image_path = os.path.join(IMAGES_DIR, img_file)
            # Streamlit does not support inline images in dataframe, so just mention
            text += f"\n[Image attached: {img_file}]"
        return text

    progress_display = progress.copy()
    progress_display["Remarks"] = progress_display.apply(format_remarks, axis=1)

    st.dataframe(progress_display.sort_values(by="Date", ascending=False))

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
