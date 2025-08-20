import streamlit as st
import pandas as pd
import datetime
import os
import re

# ---------- File Paths ----------
DATA_FILE = "test_cases.xlsx"
REPORTS_DIR = "reports"
IMAGES_DIR = "images"
USERS_DIR = "users"

# ---------- Ensure folders exist ----------
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(USERS_DIR, exist_ok=True)

# ---------- Initialize Test Cases ----------
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result", "Image Filename"])
    df.to_excel(DATA_FILE, index=False, engine='openpyxl')

# ---------- Load Test Cases ----------
test_cases = pd.read_excel(DATA_FILE, engine='openpyxl')

# ---------- Sidebar ----------
st.sidebar.title("🧪 Test Case Tracker")
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report"])
user = st.sidebar.text_input("Tester Name", value="Tester").strip()
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh All"):
    st.session_state.clear()
    st.experimental_rerun()

# ---------- User-specific progress file ----------
safe_user = re.sub(r'\W+', '_', user)
USER_PROGRESS_FILE = f"{USERS_DIR}/{safe_user}_progress.csv"

if not os.path.exists(USER_PROGRESS_FILE):
    pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"]).to_csv(USER_PROGRESS_FILE, index=False)

progress = pd.read_csv(USER_PROGRESS_FILE)
if not progress.empty:
    progress["Date"] = pd.to_datetime(progress["Date"], errors='coerce')

# ---------- Helper Functions ----------
def generate_next_id():
    if test_cases.empty:
        return "TC001"
    ids = test_cases["Test Case ID"].dropna().tolist()
    nums = [int(re.sub(r"\D", "", x)) for x in ids if re.sub(r"\D", "", x).isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"TC{next_num:03d}"

def save_test_cases():
    test_cases.to_excel(DATA_FILE, index=False, engine='openpyxl')

def save_progress():
    progress.to_csv(USER_PROGRESS_FILE, index=False)

# ---------- Run Tests ----------
if menu == "Run Tests":
    st.title("✅ Run Test Cases")

    view_mode = st.radio("View Mode", ["Expanded View", "Table View"], horizontal=True)

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
                if test_key not in st.session_state:
                    st.session_state[test_key] = False

                tested = st.checkbox("Mark as Tested", key=test_key)
                remark = st.text_area("Remarks", key=f"{row['Test Case ID']}_remark")
                remark_img = st.file_uploader("Attach image with remark (optional)", type=["png", "jpg", "jpeg"], key=f"{row['Test Case ID']}_img")

                if tested and not st.session_state.get(f"{test_key}_submitted", False):
                    remark_img_filename = ""
                    if remark_img:
                        remark_img_filename = f"remark_{row['Test Case ID']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{remark_img.name}"
                        with open(os.path.join(IMAGES_DIR, remark_img_filename), "wb") as f:
                            f.write(remark_img.getbuffer())

                    new_entry = {
                        "Test Case ID": row["Test Case ID"],
                        "Date": datetime.datetime.now(),
                        "Status": "Tested",
                        "Remarks": remark,
                        "User": user,
                        "Remark Image Filename": remark_img_filename
                    }

                    progress = pd.concat([progress, pd.DataFrame([new_entry])], ignore_index=True)
                    save_progress()
                    st.session_state[f"{test_key}_submitted"] = True
                    st.success(f"{row['Test Case ID']} marked as tested.")

    else:
        st.subheader("📋 Test Cases (Table View)")
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
        imgf = st.file_uploader("Attach Image (optional)", type=["png", "jpg", "jpeg"])

        if st.button("Add"):
            global test_cases
            fn = ""
            if imgf:
                fn = f"tc_{new_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{imgf.name}"
                with open(os.path.join(IMAGES_DIR, fn), "wb") as f:
                    f.write(imgf.getbuffer())
            new = {
                "Test Case ID": new_id,
                "Page/Field": page,
                "Module": module,
                "Task": task,
                "Steps": steps,
                "Expected Result": expected,
                "Image Filename": fn
            }
            test_cases = pd.concat([test_cases, pd.DataFrame([new])], ignore_index=True)
            save_test_cases()
            st.success("Added.")

    with st.expander("⬆️ Upload Test Cases via Excel"):
        excel = st.file_uploader("Upload Excel File", type=["xlsx"])
        if excel:
            df_new = pd.read_excel(excel, engine='openpyxl')
            if all(col in df_new.columns for col in ["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result"]):
                existing_ids = test_cases["Test Case ID"].astype(str).tolist()
                new_cases = df_new[~df_new["Test Case ID"].astype(str).isin(existing_ids)]
                if not new_cases.empty:
                    test_cases = pd.concat([test_cases, new_cases], ignore_index=True)
                    save_test_cases()
                    st.success(f"Uploaded {len(new_cases)} new test cases.")
                else:
                    st.warning("All uploaded test cases already exist.")
            else:
                st.error("Missing required columns in Excel.")

    st.subheader("✏️ Edit or Delete Test Cases")
    if not test_cases.empty:
        selected = st.selectbox("Select Test Case ID", test_cases["Test Case ID"])
        row = test_cases[test_cases["Test Case ID"] == selected].iloc[0]
        page = st.text_input("Page/Field", row["Page/Field"])
        module = st.text_input("Module", row["Module"])
        task = st.text_input("Task", row["Task"])
        steps = st.text_area("Steps", row["Steps"])
        expected = st.text_area("Expected Result", row["Expected Result"])
        new_image = st.file_uploader("Replace Image", type=["png", "jpg", "jpeg"])

        if st.button("Save Changes"):
            img_fn = row["Image Filename"]
            if new_image:
                img_fn = f"tc_{selected}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{new_image.name}"
                with open(os.path.join(IMAGES_DIR, img_fn), "wb") as f:
                    f.write(new_image.getbuffer())

            test_cases.loc[test_cases["Test Case ID"] == selected, ["Page/Field", "Module", "Task", "Steps", "Expected Result", "Image Filename"]] = [page, module, task, steps, expected, img_fn]
            save_test_cases()
            st.success("Saved.")

        if st.button("Delete Test Case"):
            test_cases = test_cases[test_cases["Test Case ID"] != selected]
            save_test_cases()
            st.success("Deleted.")

# ---------- Progress Dashboard ----------
elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")

    if progress.empty:
        st.info("No progress yet.")
    else:
        today = datetime.date.today()
        today_tests = progress[progress["Date"].dt.date == today]
        week_tests = progress[progress["Date"] >= pd.to_datetime(today - datetime.timedelta(days=7))]

        st.metric("Tested Today", len(today_tests))
        st.metric("This Week", len(week_tests))
        st.metric("Total Logs", len(progress))

        tested = progress["Test Case ID"].nunique()
        total = test_cases["Test Case ID"].nunique()
        st.progress(tested / total if total else 0.0)

        st.subheader("📑 Test Logs")
        st.dataframe(progress.sort_values(by="Date", ascending=False))

# ---------- Download Report ----------
elif menu == "Download Report":
    st.title("📄 Download Report")

    if progress.empty:
        st.warning("No progress data.")
    else:
        filename = f"{REPORTS_DIR}/report_{safe_user}_{datetime.date.today().strftime('%Y%m%d')}.csv"
        progress.to_csv(filename, index=False)

        with open(filename, "rb") as f:
            st.download_button("📥 Download CSV", f, file_name=os.path.basename(filename), mime="text/csv")
        st.success("Report ready.")
        st.dataframe(progress)
