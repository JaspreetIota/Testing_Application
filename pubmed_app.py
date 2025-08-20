import streamlit as st
import pandas as pd
import datetime
import os
import re

# ---------- File Paths ----------
DATA_FILE = "test_cases.xlsx"
PROGRESS_FILE = "progress.csv"
REPORTS_DIR = "reports"

# ---------- Ensure folders exist ----------
os.makedirs(REPORTS_DIR, exist_ok=True)

# ---------- Initialize Files ----------
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result"])
    df.to_excel(DATA_FILE, index=False, engine='openpyxl')

if not os.path.exists(PROGRESS_FILE):
    progress_df = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User"])
    progress_df.to_csv(PROGRESS_FILE, index=False)

# ---------- Load Data ----------
test_cases = pd.read_excel(DATA_FILE, engine='openpyxl')
progress = pd.read_csv(PROGRESS_FILE, parse_dates=["Date"])

# ---------- Sidebar ----------
st.sidebar.title("🧪 Test Case Tracker")
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report"])

st.sidebar.markdown("---")
user = st.sidebar.text_input("Tester Name", value="Tester")

# ---------- Run Tests ----------
if menu == "Run Tests":
    st.title("✅ Run Test Cases")

    if test_cases.empty:
        st.warning("No test cases found.")
    else:
        # --- Expand/Collapse Toggle ---
        if "expand_all" not in st.session_state:
            st.session_state["expand_all"] = True  # default: expanded

        toggle_label = "🔽 Collapse All" if st.session_state["expand_all"] else "▶️ Expand All"
        if st.button(toggle_label):
            st.session_state["expand_all"] = not st.session_state["expand_all"]

        for index, row in test_cases.iterrows():
            with st.expander(f"🔹 {row['Test Case ID']} - {row['Task']}", expanded=st.session_state["expand_all"]):
                st.markdown(f"**📄 Module**: {row['Module']}")
                st.markdown(f"**📑 Page/Field**: {row['Page/Field']}")
                st.markdown(f"**📝 Steps**:\n{row['Steps']}")
                st.markdown(f"**✅ Expected Result**:\n{row['Expected Result']}")

                key = f"{row['Test Case ID']}_tested"
                tested = st.checkbox("✔️ Mark as Tested", key=key)

                remark_key = f"{row['Test Case ID']}_remark"
                remark = st.text_area("💬 Add remark (optional)", key=remark_key)

                if tested and not st.session_state.get(f"{key}_submitted", False):
                    new_entry = {
                        "Test Case ID": row["Test Case ID"],
                        "Date": datetime.date.today(),
                        "Status": "Tested",
                        "Remarks": remark,
                        "User": user
                    }
                    progress = pd.concat([progress, pd.DataFrame([new_entry])], ignore_index=True)
                    progress.to_csv(PROGRESS_FILE, index=False)
                    st.success(f"{row['Test Case ID']} marked as tested!")
                    st.session_state[f"{key}_submitted"] = True

# ---------- Edit Test Cases ----------
elif menu == "Edit Test Cases":
    st.title("📝 Edit / Add Test Cases")

    with st.expander("➕ Add New Test Case"):
        def generate_next_id():
            if test_cases.empty:
                return "TC001"
            else:
                ids = test_cases["Test Case ID"].dropna().tolist()
                numbers = [int(''.join(filter(str.isdigit, i))) for i in ids if ''.join(filter(str.isdigit, i)).isdigit()]
                next_num = max(numbers) + 1 if numbers else 1
                return f"TC{next_num:03d}"

        new_id = generate_next_id()
        st.text_input("Test Case ID", value=new_id, disabled=True)

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
            test_cases = pd.concat([test_cases, pd.DataFrame([new_row])], ignore_index=True)
            test_cases.to_excel(DATA_FILE, index=False, engine='openpyxl')
            st.success(f"Test case {new_id} added!")

    with st.expander("📤 Upload Test Cases from Excel"):
        uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
        if uploaded_file:
            try:
                uploaded_df = pd.read_excel(uploaded_file, engine='openpyxl')
                required_columns = ["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result"]
                if all(col in uploaded_df.columns for col in required_columns):
                    test_cases = pd.concat([test_cases, uploaded_df], ignore_index=True).drop_duplicates(subset="Test Case ID")
                    test_cases.to_excel(DATA_FILE, index=False, engine='openpyxl')
                    st.success("Test cases imported successfully!")
                else:
                    st.error("Uploaded file must have the correct columns.")
            except Exception as e:
                st.error(f"Error reading file: {e}")

    st.markdown("---")
    st.subheader("✏️ Edit / Delete Existing Test Case")

    if not test_cases.empty:
        edit_id = st.selectbox("Select Test Case ID", test_cases["Test Case ID"])
        row = test_cases[test_cases["Test Case ID"] == edit_id].iloc[0]

        new_task = st.text_input("Task", row["Task"])
        new_steps = st.text_area("Steps", row["Steps"])
        new_expected = st.text_area("Expected Result", row["Expected Result"])

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("💾 Save Changes"):
                test_cases.loc[test_cases["Test Case ID"] == edit_id, ["Task", "Steps", "Expected Result"]] = [new_task, new_steps, new_expected]
                test_cases.to_excel(DATA_FILE, index=False, engine='openpyxl')
                st.success("Changes saved!")

        with col2:
            if st.button("🗑️ Delete Test Case"):
                test_cases = test_cases[test_cases["Test Case ID"] != edit_id]
                test_cases.to_excel(DATA_FILE, index=False, engine='openpyxl')
                st.success(f"Test case {edit_id} deleted.")
    else:
        st.info("No test cases available.")

# ---------- Progress Dashboard ----------
elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")

    today = datetime.date.today()
    today_tests = progress[progress["Date"].dt.date == today]
    weekly_tests = progress[progress["Date"] >= pd.to_datetime(today - datetime.timedelta(days=7))]

    st.metric("✅ Tested Today", len(today_tests))
    st.metric("📅 This Week", len(weekly_tests))
    st.metric("🧾 Total Logs", len(progress))

    tested_cases = progress["Test Case ID"].nunique()
    total_cases = test_cases["Test Case ID"].nunique()

    if total_cases > 0:
        st.progress(tested_cases / total_cases)
    else:
        st.info("No test cases available to track progress.")

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
