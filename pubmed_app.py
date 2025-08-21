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
menu = st.sidebar.radio("Navigation", ["Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report"])

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

    view_mode = st.radio("Select View Mode", ["Expanded View", "Table Test View"])

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

    elif view_mode == "Table Test View":
        st.title("📋 Table Test View")

        # CSS for table header and cells
        st.markdown("""
            <style>
            .header-row > div {
                font-weight: bold;
                padding: 4px;
                border-bottom: 2px solid #ddd;
                background-color: #f0f2f6;
            }
            .data-row > div {
                padding: 4px;
                border-bottom: 1px solid #eee;
            }
            .remarks-textarea {
                resize: vertical;
                min-height: 50px;
            }
            </style>
        """, unsafe_allow_html=True)

        # Filter today's progress with user
        if "Date" in progress.columns and pd.api.types.is_datetime64_any_dtype(progress["Date"]):
            today_progress = progress[
                (progress["Date"].dt.date == today) &
                (progress["User"] == user)
            ]
        else:
            today_progress = pd.DataFrame()

        # Prepare the merged data frame for display
        merged_df = test_cases.copy()
        merged_df["Tested"] = False
        merged_df["Remarks"] = ""
        merged_df["Remark Image Filename"] = ""

        for i, row in merged_df.iterrows():
            tc_id = row["Test Case ID"]
            filtered = today_progress[today_progress["Test Case ID"] == tc_id]
            if not filtered.empty:
                merged_df.at[i, "Tested"] = filtered.iloc[-1]["Status"] == "Tested"
                merged_df.at[i, "Remarks"] = filtered.iloc[-1]["Remarks"] if pd.notna(filtered.iloc[-1]["Remarks"]) else ""
                merged_df.at[i, "Remark Image Filename"] = filtered.iloc[-1]["Remark Image Filename"] if pd.notna(filtered.iloc[-1]["Remark Image Filename"]) else ""

        # Display table headers
        headers = ["Test Case ID", "Module", "Page/Field", "Task", "Steps", "Expected Result", "Tested", "Remarks", "Upload Image"]
        col_widths = [1, 1, 1, 2, 3, 3, 1, 3, 2]
        header_cols = st.columns(col_widths)
        for col, head in zip(header_cols, headers):
            col.markdown(head)

        # Display each test case as a row
        for idx, row in merged_df.iterrows():
            tc_id = row["Test Case ID"]

            tested_key = f"{tc_id}_table_tested"
            remark_key = f"{tc_id}_table_remark"
            file_key = f"{tc_id}_table_file"

            # Initialize session_state
            if tested_key not in st.session_state:
                st.session_state[tested_key] = row["Tested"]
            if remark_key not in st.session_state:
                st.session_state[remark_key] = row["Remarks"]

            row_cols = st.columns(col_widths)

            row_cols[0].markdown(tc_id)
            row_cols[1].markdown(row["Module"])
            row_cols[2].markdown(row["Page/Field"])
            row_cols[3].markdown(row["Task"])
            row_cols[4].markdown(row["Steps"])
            row_cols[5].markdown(row["Expected Result"])

            # Tested checkbox
            tested = row_cols[6].checkbox("", value=st.session_state[tested_key], key=tested_key)

            # Remarks text area (small height)
            remark = row_cols[7].text_area("", value=st.session_state[remark_key], key=remark_key, height=60)

            # File uploader
            uploaded_file = row_cols[8].file_uploader("", type=["jpg", "jpeg", "png"], key=file_key)

            # Show thumbnail of previously uploaded image if exists
            prev_img = row["Remark Image Filename"]
            if prev_img:
                img_path = os.path.join(IMAGE_DIR, prev_img)
                if os.path.exists(img_path):
                    row_cols[8].image(img_path, width=50)

            # Save button for this row (placed below upload, in same last column)
            save_button_label = f"Save {tc_id}"
            if row_cols[8].button(save_button_label, key=f"save_{tc_id}"):
                # Save uploaded image if any
                remark_img_filename = prev_img
                if uploaded_file is not None:
                    safe_img_name = f"{tc_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{uploaded_file.name}"
                    image_path = os.path.join(IMAGE_DIR, safe_img_name)
                    with open(image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    remark_img_filename = safe_img_name

                # Add or update progress
                filtered = today_progress[today_progress["Test Case ID"] == tc_id]
                if not filtered.empty:
                    idx_prog = filtered.index[-1]
                    progress.loc[idx_prog, "Date"] = datetime.datetime.now()
                    progress.loc[idx_prog, "Status"] = "Tested" if tested else "Not Tested"
                    progress.loc[idx_prog, "Remarks"] = remark
                    progress.loc[idx_prog, "User"] = user
                    progress.loc[idx_prog, "Remark Image Filename"] = remark_img_filename
                else:
                    new_entry = {
                        "Test Case ID": tc_id,
                        "Date": datetime.datetime.now(),
                        "Status": "Tested" if tested else "Not Tested",
                        "Remarks": remark,
                        "User": user,
                        "Remark Image Filename": remark_img_filename
                    }
                    progress.loc[len(progress)] = new_entry

                save_progress()
                st.success(f"Progress saved for {tc_id}")

                # Update session state after save
                st.session_state[tested_key] = tested
                st.session_state[remark_key] = remark

elif menu == "Edit Test Cases":
    st.title("✏️ Edit Test Cases")

    st.write("Upload an Excel file to update test cases.")
    uploaded = st.file_uploader("Upload Excel", type=["xlsx"])

    if uploaded:
        df_new = pd.read_excel(uploaded, engine='openpyxl')
        if set(["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result"]).issubset(df_new.columns):
            df_new["Image Filename"] = df_new.get("Image Filename", "")
            df_new.to_excel(TEST_CASES_FILE, index=False)
            st.success("Test cases updated successfully.")
        else:
            st.error("Missing required columns.")

elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")

    if progress.empty:
        st.info("No progress data found yet.")
    else:
        # Filter progress for selected user or all users
        user_filter = st.selectbox("Filter by User", options=["All"] + sorted(progress["User"].unique()))
        filtered_prog = progress if user_filter == "All" else progress[progress["User"] == user_filter]

        if filtered_prog.empty:
            st.info("No progress data for this user.")
        else:
            st.dataframe(filtered_prog)

elif menu == "Download Report":
    st.title("📥 Download Report")

    if progress.empty:
        st.info("No progress to download.")
    else:
        csv = progress.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, file_name=f"progress_report_{user}_{today}.csv", mime='text/csv')
