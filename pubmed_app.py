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

    # Buttons to toggle views
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Expanded View"):
            st.session_state['view_mode'] = "Expanded"
    with col2:
        if st.button("Alternate Table View"):
            st.session_state['view_mode'] = "Table"

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
                upload_key = f"{tc_id}_file"

                if tested_key not in st.session_state:
                    filtered = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (pd.to_datetime(progress["Date"], errors='coerce').dt.date == today)
                    ]
                    st.session_state[tested_key] = not filtered.empty and filtered.iloc[-1]["Status"] == "Tested"

                if remark_key not in st.session_state:
                    filtered = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (pd.to_datetime(progress["Date"], errors='coerce').dt.date == today)
                    ]
                    if not filtered.empty:
                        st.session_state[remark_key] = filtered.iloc[-1]["Remarks"] if pd.notna(filtered.iloc[-1]["Remarks"]) else ""
                    else:
                        st.session_state[remark_key] = ""

                tested = st.checkbox("Mark as Tested", key=tested_key)
                remark = st.text_area("Remarks", value=st.session_state[remark_key] or "", key=remark_key)
                remark_img = st.file_uploader("Attach image (optional)", type=["jpg", "jpeg", "png"], key=upload_key)

                # Save logic
                if tested:
                    filtered = progress[
                        (progress["Test Case ID"] == tc_id) &
                        (pd.to_datetime(progress["Date"], errors='coerce').dt.date == today)
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
                        st.success("Auto-saved!")
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
                        st.success("Auto-saved!")

    elif view_mode == "Table":
        st.subheader("📋 Alternate Table View for Running Tests")
        for _, row in test_cases.iterrows():
            tc_id = row["Test Case ID"]
            cols = st.columns([2, 2, 1.5, 2, 2])

            cols[0].markdown(f"**{tc_id}**<br>{row['Task']}", unsafe_allow_html=True)
            tested = cols[1].checkbox("Tested", key=f"{tc_id}_table_tested")
            remarks = cols[2].text_input("Remarks", key=f"{tc_id}_table_remark")
            uploaded_file = cols[3].file_uploader("Upload", type=["jpg", "jpeg", "png"], key=f"{tc_id}_table_file")
            if tested:
                filtered = progress[
                    (progress["Test Case ID"] == tc_id) &
                    (pd.to_datetime(progress["Date"], errors='coerce').dt.date == today)
                ].copy()

                remark_img_filename = ""
                if uploaded_file:
                    safe_img_name = f"{tc_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{uploaded_file.name}"
                    image_path = os.path.join(IMAGE_DIR, safe_img_name)
                    with open(image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    remark_img_filename = safe_img_name

                if filtered.empty:
                    progress.loc[len(progress)] = {
                        "Test Case ID": tc_id,
                        "Date": datetime.datetime.now(),
                        "Status": "Tested",
                        "Remarks": remarks,
                        "User": user,
                        "Remark Image Filename": remark_img_filename
                    }
                else:
                    idx = filtered.index[-1]
                    progress.at[idx, "Remarks"] = remarks
                    progress.at[idx, "Remark Image Filename"] = remark_img_filename
                    progress.at[idx, "Date"] = datetime.datetime.now()
                    progress.at[idx, "Status"] = "Tested"
                    progress.at[idx, "User"] = user
                save_progress()

# ---------- EDIT TEST CASES ----------
elif menu == "Edit Test Cases":
    st.title("📝 Edit / Add Test Cases")

    st.subheader("Edit Existing Test Cases")
    edited_df = st.experimental_data_editor(test_cases, num_rows="dynamic")
    if st.button("Save Edits"):
        edited_df.to_excel(TEST_CASES_FILE, index=False, engine='openpyxl')
        st.success("Test cases updated!")

    st.subheader("Add New Test Case")
    with st.form("add_test_case_form"):
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
        submitted = st.form_submit_button("Add Test Case")

        if submitted:
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
        progress["Date"] = pd.to_datetime(progress["Date"], errors="coerce")
        today = datetime.date.today()
        today_tests = progress[progress["Date"].dt.date == today].copy()
        week_tests = progress[progress["Date"] >= datetime.datetime.now() - datetime.timedelta(days=7)].copy()

        st.metric("Tested Today", len(today_tests))
        st.metric("Tested This Week", len(week_tests))
        st.metric("Total Logged", len(progress))

        tested = progress["Test Case ID"].nunique()
        total = test_cases["Test Case ID"].nunique()
        st.progress(tested / total if total else 0)

        merged = pd.merge(progress, test_cases, on="Test Case ID", how="left")
        st.dataframe(merged)

# ---------- REPORT ----------
elif menu == "Download Report":
    st.title("📄 Download Test Report")

    if progress.empty:
        st.warning("No report available.")
    else:
        report_file = os.path.join(PROGRESS_DIR, f"report_{user}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        merged = pd.merge(progress, test_cases, on="Test Case ID", how="left")
        merged.to_csv(report_file, index=False)
        st.success("Report ready!")

        with open(report_file, "rb") as f:
            st.download_button("📥 Download CSV", f, file_name=os.path.basename(report_file), mime="text/csv")
