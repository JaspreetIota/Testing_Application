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

# ---------- UTILITIES ----------
def safe_to_datetime(df, col):
    if col in df.columns:
        return pd.to_datetime(df[col], errors='coerce')
    else:
        return pd.Series(pd.NaT, index=df.index)

def get_user_progress_file(user):
    safe_user = re.sub(r'\W+', '_', user)
    return os.path.join(PROGRESS_DIR, f"{safe_user}_progress.csv")

# ---------- LOAD USER ----------
st.sidebar.title("🧪 Test Case Tracker")
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report", "Manage Users"])

user = st.sidebar.text_input("Tester Name", value="Tester").strip()
if not user:
    st.warning("Please enter your name.")
    st.stop()

progress_file = get_user_progress_file(user)

# ---------- LOAD TEST CASES ----------
if not os.path.exists(TEST_CASES_FILE):
    # Create empty structure if not exists
    pd.DataFrame(columns=["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result", "Image Filename"]).to_excel(TEST_CASES_FILE, index=False)

test_cases = pd.read_excel(TEST_CASES_FILE, engine='openpyxl')
if "Image Filename" not in test_cases.columns:
    test_cases["Image Filename"] = ""

# ---------- LOAD PROGRESS ----------
def load_progress():
    if os.path.exists(progress_file) and os.path.getsize(progress_file) > 0:
        df = pd.read_csv(progress_file)
        df["Date"] = safe_to_datetime(df, "Date")
        return df
    else:
        return pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"])

progress = load_progress()

def save_progress():
    progress.to_csv(progress_file, index=False)

def reset_progress_for_user():
    if os.path.exists(progress_file):
        os.remove(progress_file)
    global progress
    progress = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"])
    save_progress()
    # Clear session states related to test cases
    for key in list(st.session_state.keys()):
        if any(key.endswith(suffix) for suffix in ["_tested", "_remark", "_file", "_table_tested", "_table_remark", "_table_file"]):
            del st.session_state[key]

# ---------- APP ----------
today = datetime.date.today()

if menu == "Run Tests":
    st.title("✅ Run Test Cases")

    # Reset Progress Button
    if st.button("Reset Progress for Today"):
        reset_progress_for_user()
        st.success("Progress reset for this user.")
        st.experimental_rerun()

    view_mode = st.radio("Select View Mode", ["Expanded View"])

    if view_mode == "Expanded View":
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

                # Load existing progress for this test case today
                if tested_key not in st.session_state:
                    if "Date" in progress.columns and pd.api.types.is_datetime64_any_dtype(progress["Date"]):
                        filtered = progress[
                            (progress["Test Case ID"] == tc_id) &
                            (progress["Date"].dt.date == today) &
                            (progress["User"] == user)
                        ]
                    else:
                        filtered = pd.DataFrame()

                    st.session_state[tested_key] = not filtered.empty and filtered.iloc[-1]["Status"] == "Tested"

                if remark_key not in st.session_state:
                    if "Date" in progress.columns and pd.api.types.is_datetime64_any_dtype(progress["Date"]):
                        filtered = progress[
                            (progress["Test Case ID"] == tc_id) &
                            (progress["Date"].dt.date == today) &
                            (progress["User"] == user)
                        ]
                    else:
                        filtered = pd.DataFrame()

                    if not filtered.empty:
                        st.session_state[remark_key] = filtered.iloc[-1]["Remarks"] if pd.notna(filtered.iloc[-1]["Remarks"]) else ""
                    else:
                        st.session_state[remark_key] = ""

                tested = st.checkbox("Mark as Tested", key=tested_key)
                remark = st.text_area("Remarks", value=st.session_state[remark_key], key=remark_key)
                remark_img = st.file_uploader("Attach image (optional)", type=["jpg", "jpeg", "png"], key=file_key)

                if st.button(f"Save {tc_id} Progress"):
                    # Save or update progress for today & this test case
                    if "Date" in progress.columns and pd.api.types.is_datetime64_any_dtype(progress["Date"]):
                        filtered = progress[
                            (progress["Test Case ID"] == tc_id) &
                            (progress["Date"].dt.date == today) &
                            (progress["User"] == user)
                        ].copy()
                    else:
                        filtered = pd.DataFrame()

                    remark_img_filename = ""
                    if not filtered.empty:
                        idx = filtered.index[-1]
                        remark_img_filename = progress.at[idx, "Remark Image Filename"]
                    else:
                        idx = None

                    if remark_img:
                        safe_img_name = f"{tc_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{remark_img.name}"
                        image_path = os.path.join(IMAGE_DIR, safe_img_name)
                        with open(image_path, "wb") as f:
                            f.write(remark_img.getbuffer())
                        remark_img_filename = safe_img_name

                    new_entry = {
                        "Test Case ID": tc_id,
                        "Date": datetime.datetime.now(),
                        "Status": "Tested" if tested else "Not Tested",
                        "Remarks": remark,
                        "User": user,
                        "Remark Image Filename": remark_img_filename
                    }

                    if idx is None:
                        progress.loc[len(progress)] = new_entry
                    else:
                        progress.loc[idx] = new_entry

                    save_progress()
                    st.success(f"{tc_id} progress saved.")

elif menu == "Edit Test Cases":
    st.title("📝 Edit / Add Test Cases")

    # Add New Test Case
    with st.expander("Add New Test Case"):
        def generate_next_id():
            if test_cases.empty:
                return "TC001"
            nums = [int(re.sub(r"\D", "", str(x))) for x in test_cases["Test Case ID"] if re.sub(r"\D", "", str(x)).isdigit()]
            return f"TC{max(nums) + 1:03d}" if nums else "TC001"

        new_tc_id = generate_next_id()
        new_page_field = st.text_input("Page/Field")
        new_module = st.text_input("Module")
        new_task = st.text_input("Task")
        new_steps = st.text_area("Steps")
        new_expected = st.text_area("Expected Result")
        new_image_file = st.file_uploader("Upload Image for Test Case", type=["jpg", "jpeg", "png"])

        if st.button("Add Test Case"):
            if not new_task.strip():
                st.error("Task is required.")
            else:
                img_filename = ""
                if new_image_file:
                    safe_name = f"{new_tc_id}_{new_image_file.name}"
                    img_path = os.path.join(IMAGE_DIR, safe_name)
                    with open(img_path, "wb") as f:
                        f.write(new_image_file.getbuffer())
                    img_filename = safe_name

                new_row = {
                    "Test Case ID": new_tc_id,
                    "Page/Field": new_page_field,
                    "Module": new_module,
                    "Task": new_task,
                    "Steps": new_steps,
                    "Expected Result": new_expected,
                    "Image Filename": img_filename
                }
                test_cases.loc[len(test_cases)] = new_row
                test_cases.to_excel(TEST_CASES_FILE, index=False)
                st.success(f"Test case {new_tc_id} added.")
                st.experimental_rerun()

    st.markdown("---")
    st.write("### Existing Test Cases")
    edited_test_cases = st.data_editor(test_cases, num_rows="dynamic", use_container_width=True)

    if st.button("Save Edited Test Cases"):
        edited_test_cases.to_excel(TEST_CASES_FILE, index=False)
        st.success("Test cases saved.")

elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")

    # Show all progress for this user
    st.write(f"Progress for **{user}**")

    if progress.empty:
        st.info("No progress recorded yet.")
    else:
        st.dataframe(progress.sort_values(by="Date", ascending=False))

elif menu == "Download Report":
    st.title("📥 Download Report")

    if progress.empty:
        st.info("No progress data to download.")
    else:
        csv = progress.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Progress CSV",
            data=csv,
            file_name=f"{user}_progress_report_{today}.csv",
            mime="text/csv"
        )
elif menu == "Manage Users":
    st.title("👥 Manage Users")

    # List existing users from progress files
    user_files = [f for f in os.listdir(PROGRESS_DIR) if f.endswith("_progress.csv")]
    existing_users = [re.sub(r"_progress\.csv$", "", f).replace("_", " ") for f in user_files]

    st.subheader("Existing Users")
    if not existing_users:
        st.info("No users found.")
    else:
        for username in existing_users:
            col1, col2 = st.columns([3, 1])
            col1.write(username)
            if col2.button("Delete", key=f"del_{username}"):
                safe_user = re.sub(r'\W+', '_', username)
                filepath = get_user_progress_file(safe_user)
                try:
                    os.remove(filepath)
                    st.success(f"Deleted progress for user: {username}")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error deleting user file: {e}")

    st.divider()
    st.subheader("Add New User")
    new_user = st.text_input("Enter new user name").strip()
    if st.button("Add User"):
        if not new_user:
            st.warning("User name cannot be empty.")
        else:
            safe_user = re.sub(r'\W+', '_', new_user)
            new_user_file = get_user_progress_file(safe_user)
            if os.path.exists(new_user_file):
                st.warning("User already exists.")
            else:
                # Create empty progress file for the new user
                empty_progress = pd.DataFrame(columns=["Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"])
                empty_progress.to_csv(new_user_file, index=False)
                st.success(f"User '{new_user}' added.")
                st.experimental_rerun()
