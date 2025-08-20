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

# Ensure folders exist
for d in [REPORTS_DIR, IMAGES_DIR]:
    os.makedirs(d, exist_ok=True)

# Initialize files
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=[
        "Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result", "Image Filename"
    ]).to_excel(DATA_FILE, index=False, engine="openpyxl")

if not os.path.exists(PROGRESS_FILE):
    pd.DataFrame(columns=[
        "Test Case ID", "Date", "Status", "Remarks", "User", "Remark Image Filename"
    ]).to_csv(PROGRESS_FILE, index=False)

# Load data
test_cases = pd.read_excel(DATA_FILE, engine="openpyxl")
progress = pd.read_csv(PROGRESS_FILE)
if not progress.empty:
    progress["Date"] = pd.to_datetime(progress["Date"], errors="coerce")

# Sidebar
st.sidebar.title("🧪 Test Case Tracker")
menu = st.sidebar.radio("Navigation", [
    "Run Tests", "Edit Test Cases", "Progress Dashboard", "Download Report"
])
st.sidebar.markdown("---")
user = st.sidebar.text_input("Tester Name", value="Tester")

# Helper functions
def generate_next_id():
    if test_cases.empty:
        return "TC001"
    ids = test_cases["Test Case ID"].dropna().astype(str)
    nums = [int(re.sub(r"\D", "", i)) for i in ids if re.sub(r"\D", "", i).isdigit()]
    return f"TC{max(nums, default=0) + 1:03d}"

def save_test_cases():
    test_cases.to_excel(DATA_FILE, index=False, engine="openpyxl")

def save_progress():
    progress.to_csv(PROGRESS_FILE, index=False)

# Run Tests
if menu == "Run Tests":
    st.title("✅ Run Test Cases")

    view = st.radio("View Mode:", ["Expanded", "Table"], horizontal=True)

    # Persistent state for checked boxes and remarks
    if "form_state" not in st.session_state:
        st.session_state.form_state = {}

    def refresh_inputs():
        st.session_state.form_state = {}
        st.experimental_rerun()

    st.button("Refresh Inputs", on_click=refresh_inputs)

    if view == "Expanded":
        if 'all_open' not in st.session_state:
            st.session_state.all_open = True
        c1, c2 = st.columns(2)
        c1.button("Expand All", on_click=lambda: st.session_state.update(all_open=True))
        c2.button("Collapse All", on_click=lambda: st.session_state.update(all_open=False))

        for _, row in test_cases.iterrows():
            tcid = row["Test Case ID"]
            key_checkbox = f"{tcid}_chk"
            key_remark = f"{tcid}_rmk"
            key_img = f"{tcid}_img"

            if key_checkbox not in st.session_state.form_state:
                st.session_state.form_state[key_checkbox] = False
            if key_remark not in st.session_state.form_state:
                st.session_state.form_state[key_remark] = ""
            if key_img not in st.session_state.form_state:
                st.session_state.form_state[key_img] = None

            with st.expander(f"{tcid} – {row['Task']}", expanded=st.session_state.all_open):
                st.markdown(f"**Module:** {row['Module']}\n\n**Page:** {row['Page/Field']}")
                st.write("**Steps:**", row["Steps"])
                st.write("**Expected:**", row["Expected Result"])
                img_fn = row.get("Image Filename", "")
                if pd.notna(img_fn):
                    img_path = os.path.join(IMAGES_DIR, img_fn)
                    if os.path.exists(img_path):
                        st.image(img_path, caption="Case Image", use_column_width=True)

                st.session_state.form_state[key_checkbox] = st.checkbox(
                    "Mark Tested", value=st.session_state.form_state[key_checkbox], key=key_checkbox
                )
                st.session_state.form_state[key_remark] = st.text_area(
                    "Remarks (optional)", value=st.session_state.form_state[key_remark], key=key_remark
                )
                uploaded = st.file_uploader(
                    "Attach Remark Image (optional)", type=["png","jpg","jpeg"], key=key_img
                )
                st.session_state.form_state[key_img] = uploaded

        if st.button("Submit Results"):
            for _, row in test_cases.iterrows():
                tcid = row["Test Case ID"]
                chk = st.session_state.form_state.get(f"{tcid}_chk", False)
                if chk:
                    rmk = st.session_state.form_state.get(f"{tcid}_rmk", "")
                    imgf = st.session_state.form_state.get(f"{tcid}_img")
                    imgfn = ""
                    if imgf:
                        safe = f"remark_{tcid}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{imgf.name}"
                        path = os.path.join(IMAGES_DIR, safe)
                        with open(path, "wb") as f:
                            f.write(imgf.getbuffer())
                        imgfn = safe
                    new = {
                        "Test Case ID": tcid,
                        "Date": datetime.date.today(),
                        "Status": "Tested",
                        "Remarks": rmk,
                        "User": user,
                        "Remark Image Filename": imgfn
                    }
                    global progress
                    progress = pd.concat([progress, pd.DataFrame([new])], ignore_index=True)
            save_progress()
            st.success("Results submitted!")

    else:  # Table view
        merged = test_cases.copy()
        st.dataframe(merged.drop(columns=["Image Filename"], errors="ignore"))
        st.info("Switch to Expanded view to submit testing.")

# Edit Test Cases
elif menu == "Edit Test Cases":
    st.title("📝 Edit / Add Test Cases")
    with st.expander("Add New Test Case"):
        nid = generate_next_id()
        st.text_input("Test Case ID", value=nid, disabled=True)
        page = st.text_input("Page/Field")
        module = st.text_input("Module")
        task = st.text_input("Task")
        steps = st.text_area("Steps")
        expected = st.text_area("Expected Result")
        imgf = st.file_uploader("Attach Image", type=["png","jpg","jpeg"])
        if st.button("Add"):
            fn = ""
            if imgf:
                fn = f"tc_{nid}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{imgf.name}"
                with open(os.path.join(IMAGES_DIR, fn), "wb") as f:
                    f.write(imgf.getbuffer())
            new = {
                "Test Case ID": nid, "Page/Field": page, "Module": module,
                "Task": task, "Steps": steps, "Expected Result": expected,
                "Image Filename": fn
            }
            global test_cases
            test_cases = pd.concat([test_cases, pd.DataFrame([new])], ignore_index=True)
            save_test_cases()
            st.success("Added.")

    with st.expander("Upload via Excel"):
        file = st.file_uploader("Excel file (.xlsx)", type="xlsx")
        if file:
            df_new = pd.read_excel(file, engine="openpyxl")
            req = ["Test Case ID", "Page/Field", "Module", "Task", "Steps", "Expected Result"]
            if all(c in df_new.columns for c in req):
                existing = test_cases["Test Case ID"].astype(str).tolist()
                newc = df_new[~df_new["Test Case ID"].astype(str).isin(existing)]
                if not newc.empty:
                    test_cases = pd.concat([test_cases, newc], ignore_index=True)
                    save_test_cases()
                    st.success(f"Imported {len(newc)} new cases.")
                else:
                    st.warning("No new test cases in upload.")
            else:
                st.error(f"Missing columns: {set(req)-set(df_new.columns)}")

    st.subheader("Edit/Delete Existing")
    if not test_cases.empty:
        sel = st.selectbox("Test Case ID", test_cases["Test Case ID"])
        row = test_cases[test_cases["Test Case ID"] == sel].iloc[0]
        page = st.text_input("Page/Field", row["Page/Field"])
        module = st.text_input("Module", row["Module"])
        task = st.text_input("Task", row["Task"])
        steps = st.text_area("Steps", row["Steps"])
        expected = st.text_area("Expected Result", row["Expected Result"])
        imgf2 = st.file_uploader("Replace Image", type=["png","jpg","jpeg"])
        if st.button("Save Changes"):
            fn = row["Image Filename"]
            if imgf2:
                fn = f"tc_{sel}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{imgf2.name}"
                with open(os.path.join(IMAGES_DIR, fn), "wb") as f:
                    f.write(imgf2.getbuffer())
            test_cases.loc[test_cases["Test Case ID"]==sel, ["Page/Field","Module","Task","Steps","Expected Result","Image Filename"]] = [page,module,task,steps,expected,fn]
            save_test_cases()
            st.success("Saved.")
        if st.button("Delete Test Case"):
            test_cases = test_cases[test_cases["Test Case ID"]!=sel]
            save_test_cases()
            st.success("Deleted.")

# Progress Dashboard
elif menu == "Progress Dashboard":
    st.title("📊 Progress Dashboard")
    if progress.empty:
        st.info("No progress yet.")
    else:
        today = datetime.date.today()
        td = progress[progress["Date"].dt.date == today]
        wk = progress[progress["Date"] >= today - datetime.timedelta(days=7)]
        st.metric("Tested Today", len(td))
        st.metric("Tested This Week", len(wk))
        st.metric("Total Logs", len(progress))
        st.progress(progress["Test Case ID"].nunique() / max(1, test_cases["Test Case ID"].nunique()))
        st.subheader("History")
        df = progress.copy()
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
        st.dataframe(df.sort_values(by="Date", ascending=False))

# Download Report
elif menu == "Download Report":
    st.title("📄 Generate Report")
    filt = progress if not user.strip() else progress[progress["User"]==user]
    if filt.empty:
        st.info("No data for this user.")
    else:
        date_str = datetime.date.today().strftime("%Y%m%d")
        uf = re.sub(r"\W+", "_", user)
        fname = f"{REPORTS_DIR}/report_{uf}_{date_str}.csv"
        filt.to_csv(fname, index=False)
        st.success("Report ready")
        st.dataframe(filt)
        with open(fname, "rb") as f:
            st.download_button("Download CSV", f, file_name=os.path.basename(fname), mime="text/csv")
