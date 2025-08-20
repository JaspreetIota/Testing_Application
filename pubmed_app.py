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
    df = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"])
    df.to_csv(PROGRESS_FILE, index=False)

# ---------- Load Data ----------
test_cases = pd.read_excel(DATA_FILE, engine='openpyxl')
progress = pd.read_csv(PROGRESS_FILE)
if not progress.empty:
    progress["Date"] = pd.to_datetime(progress["Date"], errors='coerce')

# ---------- Sidebar ----------
st.sidebar.title("🧪 Test Case Tracker")
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report"])
st.sidebar.markdown("---")
user = st.sidebar.text_input("Tester Name", value="Tester").strip()
if user == "":
    st.sidebar.warning("Please enter a Tester Name")

# ---------- Helper Functions ----------
def generate_next_id():
    if test_cases.empty:
        return "TC001"
    ids = test_cases["Test Case ID"].dropna().tolist()
    nums = [int(re.sub(r"\D", "", x)) for x in ids if re.sub(r"\D", "", x).isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"TC{next_num:03d}"

def save_test_cases(df):
    df.to_excel(DATA_FILE, index=False, engine='openpyxl')

def save_progress(df):
    df.to_csv(PROGRESS_FILE, index=False)

# ---------- Run Tests ----------
if menu == "Run Tests":
    st.title(f"✅ Run Test Cases - User: {user}")

    if user == "":
        st.error("Enter Tester Name in sidebar to proceed.")
    else:
        # Initialize session state storage for inputs if not present
        if "tested" not in st.session_state:
            st.session_state["tested"] = {}
        if "remarks" not in st.session_state:
            st.session_state["remarks"] = {}
        if "remark_images" not in st.session_state:
            st.session_state["remark_images"] = {}

        tested = st.session_state["tested"]
        remarks = st.session_state["remarks"]
        remark_images = st.session_state["remark_images"]

        # Buttons for Expand/Collapse and Refresh Inputs
        col1, col2, col3 = st.columns([1,1,2])
        with col1:
            if st.button("Expand All"):
                st.session_state["expanded_state"] = True
        with col2:
            if st.button("Collapse All"):
                st.session_state["expanded_state"] = False
        with col3:
            if st.button("🔄 Clear Inputs (Refresh)"):
                st.session_state["tested"] = {}
                st.session_state["remarks"] = {}
                st.session_state["remark_images"] = {}
                st.experimental_rerun()

        if "expanded_state" not in st.session_state:
            st.session_state["expanded_state"] = True

        # Show Save Button at top
        if st.button("💾 Save Test Progress"):
            # Load existing progress
            if os.path.exists(PROGRESS_FILE):
                user_progress = pd.read_csv(PROGRESS_FILE)
                if not user_progress.empty:
                    user_progress["Date"] = pd.to_datetime(user_progress["Date"], errors='coerce')
            else:
                user_progress = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"])

            today = datetime.date.today()

            for tc_id in tested:
                if tested[tc_id]:
                    remark = remarks.get(tc_id, "")
                    remark_img_file = remark_images.get(tc_id, None)
                    remark_img_filename = ""

                    # Save remark image if uploaded
                    if remark_img_file is not None:
                        safe_name = f"remark_{tc_id}_{user}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{remark_img_file.name}"
                        with open(os.path.join(IMAGES_DIR, safe_name), "wb") as f:
                            f.write(remark_img_file.getbuffer())
                        remark_img_filename = safe_name

                    # Update existing entry or add new
                    existing_idx = user_progress[
                        (user_progress["Test Case ID"] == tc_id) &
                        (user_progress["Date"].dt.date == today) &
                        (user_progress["User"] == user)
                    ].index

                    new_entry = {
                        "Test Case ID": tc_id,
                        "Date": today,
                        "Status": "Tested",
                        "Remarks": remark,
                        "User": user,
                        "Remark Image Filename": remark_img_filename
                    }

                    if len(existing_idx) > 0:
                        idx = existing_idx[0]
                        for k, v in new_entry.items():
                            user_progress.at[idx, k] = v
                    else:
                        user_progress = pd.concat([user_progress, pd.DataFrame([new_entry])], ignore_index=True)

            save_progress(user_progress)
            st.success("Test progress saved successfully!")

        # Show test cases with inputs
        for idx, row in test_cases.iterrows():
            tc_id = row["Test Case ID"]
            with st.expander(f"{tc_id} - {row['Task']}", expanded=st.session_state["expanded_state"]):
                st.markdown(f"**Module:** {row['Module']}")
                st.markdown(f"**Page/Field:** {row['Page/Field']}")
                st.markdown(f"**Steps:** {row['Steps']}")
                st.markdown(f"**Expected Result:** {row['Expected Result']}")

                if pd.notna(row.get("Image Filename", "")) and row["Image Filename"]:
                    img_path = os.path.join(IMAGES_DIR, row["Image Filename"])
                    if os.path.exists(img_path):
                        st.image(img_path, caption="Attached Image", use_column_width=True)

                # Checkbox for marking tested
                tested[tc_id] = st.checkbox("Mark as Tested", key=f"tested_{tc_id}", value=tested.get(tc_id, False))

                # Remarks textarea
                remarks[tc_id] = st.text_area("Remarks", key=f"remark_{tc_id}", value=remarks.get(tc_id, ""))

                # Remark image uploader
                remark_images[tc_id] = st.file_uploader("Attach image with remark (optional)", type=["png", "jpg", "jpeg"], key=f"remark_img_{tc_id}", accept_multiple_files=False)

        # Save session state back
        st.session_state["tested"] = tested
        st.session_state["remarks"] = remarks
        st.session_state["remark_images"] = remark_images

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
            test_cases = pd.concat([test_cases, pd.DataFrame([new_row])], ignore_index=True)
            save_test_cases(test_cases)
            st.success("Test case added!")

    with st.expander("⬆️ Upload Test Cases via Excel"):
        excel = st.file_uploader("Upload Excel File", type=["xlsx"])
        if excel:
            df_new = pd.read_excel(excel, engine='openpyxl')
            required_cols = ["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result"]
            if all(col in df_new.columns for col in required_cols):
                existing_ids = test_cases["Test Case ID"].astype(str).tolist()
                new_cases = df_new[~df_new["Test Case ID"].astype(str).isin(existing_ids)]
                if not new_cases.empty:
                    test_cases = pd.concat([test_cases, new_cases], ignore_index=True)
                    save_test_cases(test_cases)
                    st.success(f"Uploaded {len(new_cases)} new test cases.")
                else:
                    st.warning("All uploaded test cases already exist.")
            else:
                st.error(f"Required columns missing in Excel file: {required_cols}")

    st.subheader("✏️ Edit or Delete Test Cases")
    if not test_cases.empty:
        selected = st.selectbox("Select Test Case ID", test_cases["Test Case ID"])
        row = test_cases[test_cases["Test Case ID"] == selected].iloc[0]

        page = st.text_input("Page/Field", row["Page/Field"])
        module = st.text_input("Module", row["Module"])
        task = st.text_input("Task", row["Task"])
        steps = st.text_area("Steps", row["Steps"])
        expected = st.text_area("Expected Result", row["Expected Result"])
        new_image = st.file_uploader("Replace Image (optional)", type=["png", "jpg", "jpeg"])

        if st.button("Save Changes"):
            image_filename = row["Image Filename"]
            if new_image:
                safe_name = f"testcase_{selected}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{new_image.name}"
                with open(os.path.join(IMAGES_DIR, safe_name), "wb") as f:
                    f.write(new_image.getbuffer())
                image_filename = safe_name

            test_cases.loc[test_cases["Test Case ID"] == selected, ["Page/Field", "Module", "Task", "Steps", "Expected Result", "Image Filename"]] = [page, module, task, steps, expected, image_filename]
            save_test_cases(test_cases)
            st.success("Changes saved.")

        if st.button("Delete Test Case"):
            test_cases = test_cases[test_cases["Test Case ID"] != selected]
            save_test_cases(test_cases)
            st.success("Test case deleted.")

# ---------- Progress Dashboard ----------
elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")

    if user == "":
        st.error("Enter Tester Name in sidebar to proceed.")
    else:
        user_progress = progress[progress["User"] == user] if not progress.empty else pd.DataFrame()
        if user_progress.empty:
            st.info("No progress found for this user.")
        else:
            user_progress["Date"] = pd.to_datetime(user_progress["Date"])
            st.dataframe(user_progress.sort_values(["Date", "Test Case ID"], ascending=[False, True]))

            st.subheader("Summary")
            summary = user_progress.groupby(["Status"]).size().reset_index(name="Count")
            st.bar_chart(data=summary.set_index("Status"))

# ---------- Download Report ----------
elif menu == "Download Report":
    st.title("📥 Download Test Reports")

    if user == "":
        st.error("Enter Tester Name in sidebar to proceed.")
    else:
        user_progress = progress[progress["User"] == user] if not progress.empty else pd.DataFrame()
        if user_progress.empty:
            st.info("No reports available for this user.")
        else:
            # Show dates available for report download
            dates = user_progress["Date"].dt.date.unique()
            selected_date = st.selectbox("Select Date", sorted(dates, reverse=True))

            report_data = user_progress[user_progress["Date"].dt.date == selected_date]

            if not report_data.empty:
                csv = report_data.to_csv(index=False)
                st.download_button("Download CSV Report", csv, file_name=f"report_{user}_{selected_date}.csv", mime="text/csv")

                st.subheader("Report Preview")
                for _, row in report_data.iterrows():
                    st.markdown(f"**Test Case ID:** {row['Test Case ID']}")
                    st.markdown(f"**Status:** {row['Status']}")
                    st.markdown(f"**Remarks:** {row['Remarks']}")
                    if pd.notna(row["Remark Image Filename"]) and row["Remark Image Filename"]:
                        img_path = os.path.join(IMAGES_DIR, row["Remark Image Filename"])
                        if os.path.exists(img_path):
                            st.image(img_path, caption="Remark Image", use_column_width=True)
                    st.markdown("---")
