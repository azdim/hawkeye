import pandas as pd
import requests
import streamlit as st
from datetime import datetime

from data_generator import generate_trade_data
from matching_engine import reconcile_trades

st.set_page_config(
    page_title="Kawkeye | Trade Recon",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
.block-container {padding-top: 1rem;}
div[data-testid="stMetricValue"] {
    font-family: "Consolas", "Courier New", monospace;
}
section[data-testid="stSidebar"] {
    border-right: 1px solid #2a2a2a;
}
section[data-testid="stSidebar"] .stFileUploader {
    border: 1px dashed #5a5a5a;
    padding: 0.5rem;
    border-radius: 0.5rem;
}
</style>
""",
    unsafe_allow_html=True,
)


def sanitize_break_details(break_row):
    """Convert pandas missing values to JSON-safe None."""
    sanitized = {}
    for key, value in break_row.items():
        sanitized[key] = None if pd.isna(value) else value
    return sanitized


def normalize_ai_response(payload):
    """Normalize backend response into enterprise workflow fields."""
    status = payload.get("status")
    policy_cited = payload.get("policy_cited")
    audit_rationale = payload.get("audit_rationale")
    drafted_email = payload.get("drafted_email")
    resolution = payload.get("resolution")

    if status in {"staged_for_approval", "escalated"}:
        return {
            "status": status,
            "policy_cited": policy_cited or "Unspecified policy",
            "audit_rationale": audit_rationale or "",
            "drafted_email": drafted_email or "",
        }

    # Backward compatibility for older backend response shape: {"resolution": "..."}.
    if resolution:
        lowered = str(resolution).lower()
        if "auto-approve" in lowered or "auto approve" in lowered:
            return {
                "status": "staged_for_approval",
                "policy_cited": "Legacy mapping",
                "audit_rationale": resolution,
                "drafted_email": "",
            }
        return {
            "status": "escalated",
            "policy_cited": "Legacy mapping",
            "audit_rationale": "Escalated based on legacy backend response.",
            "drafted_email": resolution,
        }

    return {
        "status": "escalated",
        "policy_cited": "System fallback",
        "audit_rationale": "Backend returned no actionable resolution fields.",
        "drafted_email": "No actionable response returned by backend.",
    }


def fetch_ai_resolution(break_row):
    """Call backend API to resolve a specific trade break."""
    try:
        response = requests.post(
            "http://localhost:3001/resolve-break",
            json={"breakDetails": break_row},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return normalize_ai_response(payload)
    except requests.RequestException as exc:
        return {
            "status": "escalated",
            "policy_cited": "System error handling",
            "audit_rationale": "Backend API call failed during autonomous processing.",
            "drafted_email": f"API request failed: {exc}",
        }


def build_action_required_breaks(unmatched_df, mismatched_df):
    """Create a unified DataFrame for per-break expander rendering."""
    unmatched_breaks = unmatched_df.copy()
    unmatched_breaks["Break_Type"] = "Unmatched"
    unmatched_breaks["Break_Reason"] = unmatched_breaks["Missing_In"].apply(
        lambda x: f"Missing in {x}"
    )

    mismatched_breaks = mismatched_df.copy()
    mismatched_breaks["Break_Type"] = "Mismatched"

    combined = pd.concat(
        [unmatched_breaks, mismatched_breaks], ignore_index=True, sort=False
    )
    return combined


def process_breaks_autonomously(unresolved_df):
    """Run backend resolution on every break and return indexed results."""
    results = {}
    with st.status("Hawkeye Agent analyzing breaks...", expanded=True) as status:
        for index, row in unresolved_df.iterrows():
            st.write(
                f"🔍 **Processing {row.get('Ticker', 'Unknown')}** "
                f"({row.get('Side', 'Unknown')} {row.get('Quantity', 'Unknown')})..."
            )

            try:
                break_details = sanitize_break_details(row.to_dict())
                response = requests.post(
                    "http://localhost:3001/resolve-break",
                    json={"breakDetails": break_details},
                    timeout=30,
                )

                if response.status_code == 200:
                    agent_output = normalize_ai_response(response.json())
                    results[index] = agent_output

                    st.json(
                        {
                            "Decision": agent_output.get("status"),
                            "Policy Applied": agent_output.get("policy_cited"),
                            "Rationale": agent_output.get("audit_rationale"),
                        }
                    )

                    if agent_output.get("status") == "staged_for_approval":
                        st.success(
                            "✅ Auto-resolved "
                            f"{row.get('Ticker', 'Unknown')} via "
                            f"{agent_output.get('policy_cited', 'policy not provided')}"
                        )
                    elif agent_output.get("status") == "escalated":
                        st.error(
                            f"⚠️ Escalated {row.get('Ticker', 'Unknown')}. "
                            "Human intervention required."
                        )
                        if agent_output.get("drafted_email"):
                            st.info(f"📧 Drafted Email:\n{agent_output.get('drafted_email')}")
                else:
                    error_payload = {
                        "status": "escalated",
                        "policy_cited": "HTTP error handling",
                        "audit_rationale": f"Backend returned status code {response.status_code}.",
                        "drafted_email": response.text,
                    }
                    results[index] = error_payload
                    st.error(
                        "Failed to resolve "
                        f"{row.get('Ticker', 'Unknown')}: HTTP {response.status_code}"
                    )
            except Exception as exc:
                results[index] = {
                    "status": "escalated",
                    "policy_cited": "Runtime error handling",
                    "audit_rationale": "Exception occurred while calling Hawkeye Agent backend.",
                    "drafted_email": str(exc),
                }
                st.error(
                    "Failed to connect to Hawkeye Agent for "
                    f"{row.get('Ticker', 'Unknown')}: {exc}"
                )

        status.update(label="Batch processing complete.", state="complete", expanded=False)
    return results


def main():
    st.markdown(
        "<h1>👁️ Hawkeye | Autonomous Reconciliation Engine</h1>",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.title("🔌 Data Connectors")
        uploaded_pb_file = st.file_uploader(
            "Prime Broker Statement (CSV)",
            type=["csv"],
        )
        st.caption("Mocking automated SFTP drop / Email parser ingestion")
        st.caption("If hidden, use the left chevron to toggle sidebar.")

    if uploaded_pb_file is None:
        st.info("Waiting for Data: Upload a Prime Broker statement CSV to begin.")
        return

    try:
        pb_df = pd.read_csv(uploaded_pb_file)
    except Exception as exc:
        st.error(f"Unable to read uploaded CSV: {exc}")
        return

    oms_df, _ = generate_trade_data()
    perfect_matches, unmatched, mismatched = reconcile_trades(oms_df, pb_df)

    file_signature = (uploaded_pb_file.name, uploaded_pb_file.size)
    if st.session_state.get("last_ingested_signature") != file_signature:
        st.session_state["last_ingested_signature"] = file_signature
        st.toast("Data ingested and reconciled successfully!")

    total_breaks = len(unmatched) + len(mismatched)

    kpi_col_1, kpi_col_2 = st.columns(2)
    with kpi_col_1:
        st.metric("Total Trades", len(pb_df))
    with kpi_col_2:
        st.metric("Breaks", total_breaks)

    break_rows = build_action_required_breaks(unmatched, mismatched).reset_index(drop=True)
    break_rows["Break_ID"] = break_rows.index

    if "ai_break_results" not in st.session_state:
        st.session_state["ai_break_results"] = {}
    if "approved_email_break_ids" not in st.session_state:
        st.session_state["approved_email_break_ids"] = set()
    if "compliance_audit_log" not in st.session_state:
        st.session_state["compliance_audit_log"] = []
    if "committed_staged_break_ids" not in st.session_state:
        st.session_state["committed_staged_break_ids"] = set()
    if "last_autorun_signature" not in st.session_state:
        st.session_state["last_autorun_signature"] = None

    tab_action, tab_staged, tab_audit = st.tabs(
        [
            "Action Required (Exceptions)",
            "Staged by AI (Pending Approval)",
            "Compliance Audit Log",
        ]
    )

    with tab_action:
        ai_results = st.session_state["ai_break_results"]
        unresolved_df = break_rows[
            ~break_rows["Break_ID"].isin(st.session_state["committed_staged_break_ids"])
        ].copy()

        should_autorun = (
            st.session_state["last_autorun_signature"] != file_signature
            and not unresolved_df.empty
        )
        if should_autorun:
            updated_results = process_breaks_autonomously(unresolved_df)
            st.session_state["ai_break_results"].update(updated_results)
            st.session_state["last_autorun_signature"] = file_signature
        elif st.session_state["last_autorun_signature"] != file_signature:
            st.session_state["last_autorun_signature"] = file_signature

        st.subheader("Break Triage")
        ai_results = st.session_state["ai_break_results"]

        if break_rows.empty:
            st.success("No breaks found.")
        else:
            action_rows = []

            for _, row in break_rows.iterrows():
                break_id = row["Break_ID"]
                result = ai_results.get(break_id)
                is_committed = break_id in st.session_state["committed_staged_break_ids"]
                if is_committed:
                    continue
                if not result or result.get("status") != "staged_for_approval":
                    action_rows.append((row, result))

            if action_rows:
                action_required_df = pd.DataFrame([item[0] for item in action_rows]).drop(
                    columns=["Break_ID"], errors="ignore"
                )
                st.dataframe(action_required_df, width="stretch")
            else:
                st.success("No exceptions pending. All breaks are either staged or committed.")

            for row, result in action_rows:
                idx = int(row["Break_ID"])
                ticker = row.get("Ticker", "Unknown")
                break_type = row.get("Break_Type", "Break")
                reason = row.get("Break_Reason", "No reason available")
                expander_title = f"{idx + 1}. {ticker} - {break_type}"

                with st.expander(expander_title):
                    st.write(f"**Reason:** {reason}")
                    st.dataframe(
                        pd.DataFrame([row.drop(labels=["Break_ID"])]), width="stretch"
                    )

                    if result and result.get("status") == "escalated":
                        st.caption(
                            f"Policy Cited: {result.get('policy_cited', 'Unspecified policy')}"
                        )
                        st.write(result.get("audit_rationale", ""))
                        drafted_email = result.get("drafted_email", "")
                        if drafted_email:
                            st.info(drafted_email)

                        approve_key = f"approve_send_{idx}"
                        if idx in st.session_state["approved_email_break_ids"]:
                            st.success("Email approved for sending.")
                        elif st.button("Approve & Send Email", key=approve_key):
                            st.session_state["approved_email_break_ids"].add(idx)
                            st.success("Email approved for sending.")

    with tab_staged:
        st.subheader("Staged by AI (Pending Approval)")
        ai_results = st.session_state["ai_break_results"]
        staged_records = []
        for _, row in break_rows.iterrows():
            break_id = row["Break_ID"]
            result = ai_results.get(break_id)
            if (
                result
                and result.get("status") == "staged_for_approval"
                and break_id not in st.session_state["committed_staged_break_ids"]
            ):
                record = row.drop(labels=["Break_ID"]).to_dict()
                record["Resolution Action"] = "Staged for approval"
                record["Policy Cited"] = result.get("policy_cited", "")
                record["Audit Rationale"] = result.get("audit_rationale", "")
                record["Break_ID"] = break_id
                staged_records.append(record)

        if staged_records:
            staged_df = pd.DataFrame(staged_records)
            editor_columns = [
                "Break_ID",
                "TradeDate",
                "Ticker",
                "Resolution Action",
                "Policy Cited",
                "Audit Rationale",
            ]
            staged_editor_df = staged_df[editor_columns]
            edited_staged_df = st.data_editor(
                staged_editor_df,
                width="stretch",
                hide_index=True,
                key="staged_breaks_editor",
                column_config={
                    "Break_ID": None,
                    "TradeDate": st.column_config.TextColumn("TradeDate"),
                    "Ticker": st.column_config.TextColumn("Ticker"),
                    "Resolution Action": st.column_config.TextColumn(
                        "Resolution Action",
                        help="Checker may update this action prior to commit.",
                    ),
                    "Policy Cited": st.column_config.TextColumn(
                        "Policy Cited",
                        help="Checker may adjust policy citation if needed.",
                    ),
                    "Audit Rationale": st.column_config.TextColumn("Audit Rationale"),
                },
                disabled=["Break_ID", "TradeDate", "Ticker", "Audit Rationale"],
            )

            if st.button("Checker: Approve & Commit Batch", type="primary"):
                timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                for staged_record in edited_staged_df.to_dict(orient="records"):
                    break_id = staged_record.get("Break_ID")
                    if break_id is None:
                        continue
                    st.session_state["committed_staged_break_ids"].add(break_id)
                    st.session_state["compliance_audit_log"].append(
                        {
                            "Timestamp": timestamp,
                            "Ticker": staged_record.get("Ticker", "Unknown"),
                            "Resolution Action": staged_record.get(
                                "Resolution Action",
                                "Staged for approval and checker-approved",
                            ),
                            "Policy Cited": staged_record.get("Policy Cited", ""),
                            "Approved By": "Current User",
                        }
                    )
                st.success("Batch approved and committed to Compliance Audit Log.")
        else:
            st.info("No staged breaks pending approval.")

    with tab_audit:
        st.subheader("Compliance Audit Log")
        audit_log_df = pd.DataFrame(st.session_state["compliance_audit_log"])
        if audit_log_df.empty:
            st.info("No committed audit entries yet.")
        else:
            st.dataframe(
                audit_log_df[
                    [
                        "Timestamp",
                        "Ticker",
                        "Resolution Action",
                        "Policy Cited",
                        "Approved By",
                    ]
                ],
                width="stretch",
            )


if __name__ == "__main__":
    main()
