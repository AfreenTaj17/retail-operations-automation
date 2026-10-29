
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Retail Operations Dashboard",
    page_icon="📦",
    layout="wide",
)

st.title("📦 Retail Operations Dashboard")
st.caption("Stock management | Approval workflow | Audit tracking")

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Create Request", "Manage Requests", "Audit History"],
)


def api_get(path):
    response = requests.get(f"{API_URL}{path}", timeout=5)
    response.raise_for_status()
    return response.json()


def show_api_error(error):
    st.error(
        "Could not communicate with the backend API. "
        "Check that FastAPI is running at http://127.0.0.1:8000."
    )
    st.caption(f"Technical details: {error}")


if page == "Dashboard":
    st.header("Operations Overview")

    try:
        requests_data = api_get("/requests")

        total = len(requests_data)
        pending = sum(r["status"] == "Pending" for r in requests_data)
        approved = sum(r["status"] == "Approved" for r in requests_data)
        rejected = sum(r["status"] == "Rejected" for r in requests_data)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Requests", total)
        col2.metric("Pending", pending)
        col3.metric("Approved", approved)
        col4.metric("Rejected", rejected)

        st.subheader("Recent Stock Requests")

        if requests_data:
            st.dataframe(
                requests_data,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No stock requests have been created yet.")

        if st.button("Refresh Dashboard"):
            st.rerun()

    except requests.RequestException as error:
        show_api_error(error)


elif page == "Create Request":
    st.header("Create Stock Request")

    with st.form("stock_request_form"):
        item = st.text_input("Item name")
        quantity = st.number_input(
            "Quantity",
            min_value=1,
            max_value=10000,
            value=1,
            step=1,
        )
        reason = st.text_area("Reason for request")

        submitted = st.form_submit_button("Submit Request")

    if submitted:
        if not item.strip() or not reason.strip():
            st.error("Please enter an item name and reason.")
        else:
            try:
                response = requests.post(
                    f"{API_URL}/requests",
                    json={
                        "item": item.strip(),
                        "quantity": int(quantity),
                        "reason": reason.strip(),
                    },
                    timeout=5,
                )
                response.raise_for_status()
                created = response.json()

                st.success(
                    f"Request #{created['request_id']} created successfully!"
                )
                st.json(created)

            except requests.HTTPError as error:
                details = error.response.text if error.response else str(error)
                st.error(f"Request rejected by API: {details}")
            except requests.RequestException as error:
                show_api_error(error)


elif page == "Manage Requests":
    st.header("Manage Stock Requests")

    try:
        requests_data = api_get("/requests")

        if not requests_data:
            st.info("No requests available to manage.")
        else:
            for request_data in requests_data:
                request_id = request_data["request_id"]
                status_value = request_data["status"]

                with st.expander(
                    f"#{request_id} — {request_data['item']} "
                    f"({status_value})"
                ):
                    st.write(f"**Quantity:** {request_data['quantity']}")
                    st.write(f"**Reason:** {request_data['reason']}")
                    st.write(f"**Created:** {request_data['created_at']}")
                    st.write(f"**Status:** {status_value}")

                    if status_value == "Pending":
                        col1, col2 = st.columns(2)

                        if col1.button(
                            "Approve",
                            key=f"approve_{request_id}",
                        ):
                            try:
                                response = requests.post(
                                    f"{API_URL}/requests/{request_id}/approve",
                                    timeout=5,
                                )
                                response.raise_for_status()
                                st.success("Request approved.")
                                st.rerun()
                            except requests.HTTPError as error:
                                details = (
                                    error.response.text
                                    if error.response
                                    else str(error)
                                )
                                st.error(f"Approval failed: {details}")
                            except requests.RequestException as error:
                                show_api_error(error)

                        if col2.button(
                            "Reject",
                            key=f"reject_{request_id}",
                        ):
                            try:
                                response = requests.post(
                                    f"{API_URL}/requests/{request_id}/reject",
                                    timeout=5,
                                )
                                response.raise_for_status()
                                st.success("Request rejected.")
                                st.rerun()
                            except requests.HTTPError as error:
                                details = (
                                    error.response.text
                                    if error.response
                                    else str(error)
                                )
                                st.error(f"Rejection failed: {details}")
                            except requests.RequestException as error:
                                show_api_error(error)

    except requests.RequestException as error:
        show_api_error(error)


elif page == "Audit History":
    st.header("Audit History")

    try:
        requests_data = api_get("/requests")

        if not requests_data:
            st.info("No requests available.")
        else:
            request_ids = [r["request_id"] for r in requests_data]
            selected_id = st.selectbox(
                "Select request ID",
                request_ids,
            )

            audit_data = api_get(f"/requests/{selected_id}/audit")

            if audit_data:
                st.dataframe(
                    audit_data,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No audit entries found for this request.")

    except requests.RequestException as error:
        show_api_error(error)

