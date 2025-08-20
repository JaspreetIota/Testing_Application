import streamlit as st
import pandas as pd
import datetime
import os

# ---------- File Paths ----------
DATA_FILE = "test_cases.csv"
PROGRESS_FILE = "progress.csv"
REPORTS_DIR = "reports"

# ---------- Ensure required files exist ----------
os.makedirs(REPORTS_DIR, exist_ok=True)

if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result"])
    df.to_csv(DATA_FILE, index=False)

if not os.path.exists(PROGRESS_FILE):
    progress_df = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User"])
    progress_df.to_csv(PROGRESS_FILE, index=False)

# ---------- Load Data ----------
test_cases = pd.read_csv(DATA_FILE)
progress = pd.read_csv(PROGRESS_FILE)

# ---------- Sidebar ----------
st.sidebar.title("🧪 Test Case Tracker")
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report"])

st.sidebar.markdown("---")
user = st.sidebar.text_input("Tester Name", value="Tester")

# ---------- Run Tests ----------
if menu == "Run Tests":
    st.title("✅ Run Test Cases")

    for index, row in test_cases.iterrows():
        st.subheader(f"{row['Test Case ID']} - {row['Task']}")
        st.write(f"**Module**: {row['Module']}")
        st.write(f"**Steps**: {row['Steps']}")
        st.write(f"**Expected Result**: {row['Expected Result']}")

        key = f"{row['Test Case ID']}_tested"
        tested = st.checkbox("Mark as Tested", key=key)

        remark_key = f"{row['Test Case ID']}_remark"
        remark = st.text_area("Add remark (optional)", key=remark_key)

        if tested:
            new_entry = {
                "Test Case ID": row["Test Case ID"],
                "Date": datetime.date.today(),
                "Status": "Tested",
                "Remarks": remark,
                "User": user
            }
            progress = progress.append(new_entry, ignore_index=True)
            progress.to_csv(PROGRESS_FILE, index=False)
            st.success(f"{row['Test Case ID']} marked as tested!")

# ---------- Edit Test Cases ----------
elif menu == "Edit Test Cases":
    st.title("📝 Edit / Add Test Cases")

    with st.expander("➕ Add New Test Case"):
        new_id = st.text_input("Test Case ID")
        page = st.text_input("Page/Field")
        module = st.text_input("Module")
        task = st.text_input("Task")
        steps = st.text_area("Steps")
        expected = st.text_area("Expected Result")

        if st.button("Add Test Case"):
            new_row = {
                "Test Case ID": new_id,
                "Page/Field": page,
                "Module": module,
                "Task": task,
                "Steps": steps,
                "Expected Result": expected
            }
            test_cases = test_cases.append(new_row, ignore_index=True)
            test_cases.to_csv(DATA_FILE, index=False)
            st.success("Test case added!")

    st.markdown("---")
    st.subheader("✏️ Edit Existing Test Cases")
    edit_id = st.selectbox("Select Test Case ID", test_cases["Test Case ID"])

    if edit_id:
        row = test_cases[test_cases["Test Case ID"] == edit_id].iloc[0]
        new_task = st.text_input("Task", row["Task"])
        new_steps = st.text_area("Steps", row["Steps"])
        new_expected = st.text_area("Expected Result", row["Expected Result"])

        if st.button("Save Changes"):
            test_cases.loc[test_cases["Test Case ID"] == edit_id, ["Task", "Steps", "Expected Result"]] = [new_task, new_steps, new_expected]
            test_cases.to_csv(DATA_FILE, index=False)
            st.success("Changes saved!")

# ---------- Progress Dashboard ----------
elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")

    today = datetime.date.today()
    today_tests = progress[progress["Date"] == pd.to_datetime(today)]
    weekly_tests = progress[progress["Date"] >= pd.to_datetime(today - datetime.timedelta(days=7))]

    st.metric("Tested Today", len(today_tests))
    st.metric("Tested This Week", len(weekly_tests))
    st.metric("Total Tests Logged", len(progress))

    tested_cases = progress["Test Case ID"].nunique()
    total_cases = test_cases["Test Case ID"].nunique()
    st.progress(tested_cases / total_cases if total_cases else 0)

    st.subheader("🗂️ Test Case History")
    st.dataframe(progress.sort_values(by="Date", ascending=False))

# ---------- Download Report ----------
elif menu == "Download Report":
    st.title("📄 Generate & Download Report")

    user_progress = progress if user.strip() == "" else progress[progress["User"] == user]

    if user_progress.empty:
        st.info("No test progress found.")
    else:
        report_date = datetime.date.today().strftime("%Y%m%d")
        filename = f"{REPORTS_DIR}/report_{user}_{report_date}.csv"

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
