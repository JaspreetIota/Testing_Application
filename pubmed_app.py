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
user = st.sidebar.text_input("Tester Name", value="Tester")

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
    st.title("✅ Run Test Cases")

    view_mode = st.radio("Choose view mode:", ["Expanded View", "Table View"], horizontal=True)

    if view_mode == "Expanded View":
        if 'expanded_state' not in st.session_state:
            st.session_state.expanded_state = True

        col1, col2 = st.columns(2)
        if col1.button("Expand All"):
            st.session_state.expanded_state = True
        if col2.button("Collapse All"):
            st.session_state.expanded_state = False

        for idx, row in test_cases.iterrows():
            with st.expander(f"{row['Test Case ID']} - {row['Task']}", expanded=st.session_state.expanded_state):
                st.markdown(f"**Module:** {row['Module']}")
                st.markdown(f"**Page/Field:** {row['Page/Field']}")
                st.markdown(f"**Steps:** {row['Steps']}")
                st.markdown(f"**Expected Result:** {row['Expected Result']}")
                if pd.notna(row.get("Image Filename", "")):
                    img_path = os.path.join(IMAGES_DIR, row["Image Filename"])
                    if os.path.exists(img_path):
                        st.image(img_path, caption="Attached Image", use_column_width=True)

                test_key = f"{row['Test Case ID']}_tested"
                tested = st.checkbox("Mark as Tested", key=test_key)

                remark = st.text_area("Remarks", key=f"{row['Test Case ID']}_remark")
                remark_img = st.file_uploader("Attach image with remark (optional)", type=["png", "jpg", "jpeg"], key=f"{row['Test Case ID']}_img")

                if tested and not st.session_state.get(f"{test_key}_submitted", False):
                    remark_img_filename = ""
                    if remark_img is not None:
                        safe_name = f"remark_{row['Test Case ID']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{remark_img.name}"
                        with open(os.path.join(IMAGES_DIR, safe_name), "wb") as f:
                            f.write(remark_img.getbuffer())
                            remark_img_filename = safe_name
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
                            st.session_state[f"{test_key}_submitted"] = True


    else:
        st.dataframe(test_cases.drop(columns=["Image Filename"], errors="ignore"))

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
            if all(col in df_new.columns for col in ["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result"]):
                existing_ids = test_cases["Test Case ID"].astype(str).tolist()
                new_cases = df_new[~df_new["Test Case ID"].astype(str).isin(existing_ids)]
                if not new_cases.empty:
                    test_cases = pd.concat([test_cases, new_cases], ignore_index=True)
                    save_test_cases(test_cases)
                    st.success(f"Uploaded {len(new_cases)} new test cases.")
                else:
                    st.warning("All uploaded test cases already exist.")
            else:
                st.error("Required columns missing in Excel file.")

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

    if progress.empty:
        st.info("No progress data available.")
    else:
        today = datetime.date.today()
        today_tests = progress[progress["Date"].dt.date == today]
        week_tests = progress[progress["Date"] >= pd.to_datetime(today - datetime.timedelta(days=7))]

        st.metric("Tested Today", len(today_tests))
        st.metric("Tested This Week", len(week_tests))
        st.metric("Total Tests Logged", len(progress))

        tested = progress["Test Case ID"].nunique()
        total = test_cases["Test Case ID"].nunique()
        st.progress(tested / total if total else 0)

        st.subheader("🗂️ Test Case History")
        st.dataframe(progress.sort_values(by="Date", ascending=False))

# ---------- Download Report ----------
elif menu == "Download Report":
    st.title("📄 Generate & Download Report")

    filtered = progress if not user.strip() else progress[progress["User"] == user]
    if filtered.empty:
        st.info("No progress to report.")
    else:
        date_str = datetime.date.today().strftime("%Y%m%d")
        safe_user = re.sub(r'\W+', '_', user)
        report_file = f"{REPORTS_DIR}/report_{safe_user}_{date_str}.csv"

        filtered.to_csv(report_file, index=False)
        st.success(f"Report ready for {user}")
        st.dataframe(filtered)

        with open(report_file, "rb") as f:
            st.download_button("📥 Download Report", f, file_name=os.path.basename(report_file), mime="text/csv")
