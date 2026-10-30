import os
import logging
import requests
import streamlit as st

# ==========================================
# CONFIGURATION
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("retail_operations")

try:
    API_URL = st.secrets.get(
        "API_URL",
        os.getenv("API_URL", "http://127.0.0.1:8000")
    ).rstrip("/")
except Exception:
    API_URL = os.getenv(
        "API_URL",
        "http://127.0.0.1:8000"
    ).rstrip("/")

st.set_page_config(
    page_title="Retail Operations Dashboard",
    page_icon="📦",
    layout="wide",
)

# ==========================================
# SESSION STATE
# ==========================================

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "username" not in st.session_state:
    st.session_state.username = None

if "role" not in st.session_state:
    st.session_state.role = None


# ==========================================
# API HELPERS
# ==========================================

def auth_headers():
    """Return JWT authorization headers."""

    token = st.session_state.access_token

    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}"
    }


def api_request(method, path, **kwargs):
    """Send an authenticated request to the FastAPI backend."""

    headers = kwargs.pop("headers", {})

    headers.update(auth_headers())

    response = requests.request(
        method=method,
        url=f"{API_URL}{path}",
        headers=headers,
        timeout=10,
        **kwargs
    )

    response.raise_for_status()

    if response.content:
        return response.json()

    return None


def show_api_error(error):
    """Display useful API error messages."""

    if isinstance(error, requests.HTTPError):
        response = error.response
        code = response.status_code

        if code == 401:
            st.error(
                "Your session has expired or authentication failed. "
                "Please log in again."
            )
            return

        if code == 403:
            st.error(
                "Access denied. Your account does not have permission "
                "to perform this action."
            )
            return

        if code == 404:
            st.error("The requested record was not found.")
            return

        if code == 409:
            st.error(
                "This request has already been processed. "
                "Refresh the page."
            )
            return

        st.error(f"API returned HTTP {code}.")
        st.caption(response.text[:500])
        return

    st.error(
        "Could not connect to the backend. "
        "Check that FastAPI is running."
    )
    st.caption(str(error))


# ==========================================
# LOGIN
# ==========================================

def login_page():

    st.title("📦 Retail Operations System")
    st.caption("Secure stock request and approval management")

    st.subheader("Login")

    with st.form("login_form"):

        username = st.text_input("Username")

        password = st.text_input(
            "Password",
            type="password"
        )

        submitted = st.form_submit_button(
            "Login",
            use_container_width=True
        )

    if submitted:

        if not username.strip() or not password:
            st.error("Enter both username and password.")
            return

        try:
            response = requests.post(
                f"{API_URL}/login",
                json={
                    "username": username.strip(),
                    "password": password,
                },
                timeout=10,
            )

            response.raise_for_status()

            login_data = response.json()

            token = login_data["access_token"]

            # Retrieve authenticated user details.
            user_response = requests.get(
                f"{API_URL}/me",
                headers={
                    "Authorization": f"Bearer {token}"
                },
                timeout=10,
            )

            user_response.raise_for_status()

            user_data = user_response.json()

            st.session_state.access_token = token
            st.session_state.username = user_data["username"]
            st.session_state.role = user_data["role"]

            logger.info(
                "User login successful: %s",
                user_data["username"]
            )

            st.success("Login successful!")
            st.rerun()

        except requests.HTTPError as error:

            if error.response is not None:
                if error.response.status_code == 401:
                    st.error("Invalid username or password.")
                else:
                    show_api_error(error)
            else:
                show_api_error(error)

        except (requests.RequestException, KeyError) as error:
            show_api_error(error)


# ==========================================
# DASHBOARD
# ==========================================

def dashboard():

    st.header("Operations Overview")

    try:

        requests_data = api_request(
            "GET",
            "/requests"
        )

        total = len(requests_data)

        pending = sum(
            r["status"] == "Pending"
            for r in requests_data
        )

        approved = sum(
            r["status"] == "Approved"
            for r in requests_data
        )

        rejected = sum(
            r["status"] == "Rejected"
            for r in requests_data
        )

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
                hide_index=True
            )

        else:
            st.info("No stock requests available.")

        if st.button("Refresh Dashboard"):
            st.rerun()

    except requests.RequestException as error:
        show_api_error(error)


# ==========================================
# CREATE STOCK REQUEST
# ==========================================

def create_request():

    st.header("Create Stock Request")

    with st.form("stock_request_form"):

        item = st.text_input("Item name")

        quantity = st.number_input(
            "Quantity",
            min_value=1,
            max_value=10000,
            value=1,
            step=1
        )

        reason = st.text_area(
            "Reason for request"
        )

        submitted = st.form_submit_button(
            "Submit Request"
        )

    if submitted:

        if len(item.strip()) < 2:
            st.error("Item name must contain at least 2 characters.")

        elif len(reason.strip()) < 5:
            st.error("Reason must contain at least 5 characters.")

        else:

            try:

                created = api_request(
                    "POST",
                    "/requests",
                    json={
                        "item": item.strip(),
                        "quantity": int(quantity),
                        "reason": reason.strip(),
                    }
                )

                st.success(
                    f"Request #{created['request_id']} "
                    "created successfully!"
                )

                st.json(created)

            except requests.RequestException as error:
                show_api_error(error)


# ==========================================
# MANAGER REQUEST MANAGEMENT
# ==========================================

def manage_requests():

    st.header("Manage Stock Requests")

    if st.session_state.role != "manager":
        st.error("Manager permissions required.")
        return

    try:

        requests_data = api_request(
            "GET",
            "/requests"
        )

        if not requests_data:
            st.info("No requests available.")
            return

        for request_data in requests_data:

            request_id = request_data["request_id"]

            status_value = request_data["status"]

            with st.expander(
                f"#{request_id} — {request_data['item']} "
                f"({status_value})"
            ):

                st.write(
                    f"**Quantity:** {request_data['quantity']}"
                )

                st.write(
                    f"**Reason:** {request_data['reason']}"
                )

                st.write(
                    f"**Created:** {request_data['created_at']}"
                )

                st.write(
                    f"**Status:** {status_value}"
                )

                if status_value == "Pending":

                    col1, col2 = st.columns(2)

                    if col1.button(
                        "Approve",
                        key=f"approve_{request_id}"
                    ):

                        api_request(
                            "POST",
                            f"/requests/{request_id}/approve"
                        )

                        st.success("Request approved!")
                        st.rerun()

                    if col2.button(
                        "Reject",
                        key=f"reject_{request_id}"
                    ):

                        api_request(
                            "POST",
                            f"/requests/{request_id}/reject"
                        )

                        st.success("Request rejected!")
                        st.rerun()

    except requests.RequestException as error:
        show_api_error(error)


# ==========================================
# AUDIT HISTORY
# ==========================================

def audit_history():

    st.header("Audit History")

    try:

        requests_data = api_request(
            "GET",
            "/requests"
        )

        if not requests_data:
            st.info("No requests available.")
            return

        request_ids = [
            r["request_id"]
            for r in requests_data
        ]

        selected_id = st.selectbox(
            "Select Request ID",
            request_ids
        )

        audit_data = api_request(
            "GET",
            f"/requests/{selected_id}/audit"
        )

        if audit_data:

            st.dataframe(
                audit_data,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info("No audit entries found.")

    except requests.RequestException as error:
        show_api_error(error)


# ==========================================
# MAIN APPLICATION
# ==========================================

if not st.session_state.access_token:

    login_page()

else:

    username = st.session_state.username
    role = st.session_state.role

    st.title("📦 Retail Operations Dashboard")

    st.caption(
        f"Logged in as: {username} | Role: {role.title()}"
    )

    st.sidebar.title("Navigation")

    st.sidebar.success(
        f"Welcome, {username}"
    )

    if role == "manager":

        pages = [
            "Dashboard",
            "Create Request",
            "Manage Requests",
            "Audit History",
        ]

    else:

        pages = [
            "Dashboard",
            "Create Request",
            "Audit History",
        ]

    page = st.sidebar.radio(
        "Go to",
        pages
    )

    if st.sidebar.button(
        "Logout",
        use_container_width=True
    ):

        st.session_state.access_token = None
        st.session_state.username = None
        st.session_state.role = None

        st.rerun()

    st.divider()

    if page == "Dashboard":
        dashboard()

    elif page == "Create Request":
        create_request()

    elif page == "Manage Requests":
        manage_requests()

    elif page == "Audit History":
        audit_history()
