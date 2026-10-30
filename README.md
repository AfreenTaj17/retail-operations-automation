# Retail Operations Automation System

A role-based retail stock request and approval management prototype built using **Python, FastAPI, SQLite, and Streamlit**.

[![Retail Operations CI](https://github.com/AfreenTaj17/retail-operations-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/AfreenTaj17/retail-operations-automation/actions/workflows/ci.yml)

## Project Overview

Retail teams regularly handle stock requests that require review and approval from managers. Manual processes can make it difficult to track request status, enforce approval permissions, and maintain an accurate activity history.

This project demonstrates a digital workflow for managing stock requests, with separate employee and manager permissions, authenticated API access, and audit logging.

**Note:** This is an independent portfolio prototype inspired by retail operations workflows. It is not an official Tesco application or a production retail system.

## Key Features

- **User authentication:** Employee and manager login using JWT access tokens.
- **Password security:** Passwords are hashed using Argon2.
- **Role-based access control:** Employees can create and view requests; managers can approve or reject them.
- **Stock request management:** Submit requests with item names, quantities, and reasons.
- **Approval workflow:** Prevents repeated approval or rejection of completed requests.
- **Audit logging:** Records request creation and management actions.
- **REST API:** Backend developed with FastAPI and Pydantic validation.
- **Interactive dashboard:** Streamlit interface with a dark navy and teal theme.
- **Automated testing:** Pytest test suite covering authentication, validation, permissions, and request workflows.
- **CI pipeline:** GitHub Actions automatically runs tests on pushes and pull requests to `main`.

## Technology Stack

| Area | Technologies |
|---|---|
| Language | Python 3.12 |
| Backend | FastAPI |
| Frontend | Streamlit |
| Database | SQLite |
| Authentication | JWT |
| Password hashing | Argon2 |
| Validation | Pydantic |
| Testing | Pytest, FastAPI TestClient |
| API testing | Swagger UI |
| Version control | Git, GitHub |
| CI/CD | GitHub Actions |

## System Architecture

```text
              Employee / Manager
                      |
                      v
              Streamlit Frontend
                      |
                 HTTP + JWT
                      |
                      v
                FastAPI Backend
                      |
          Authentication & RBAC
                      |
             Request Management
                      |
             -----------------
             |               |
             v               v
        SQLite Database   Audit Logs
```

## Application Workflow

1. An employee registers and logs in.
2. The backend validates credentials and issues a JWT access token.
3. The employee submits a stock request.
4. The request is stored with a `Pending` status.
5. A manager logs in and reviews pending requests.
6. The manager approves or rejects a request.
7. The system records the action in the audit log.
8. Users can view request information and its activity history.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/register` | Register an employee |
| POST | `/login` | Authenticate a user |
| GET | `/me` | Retrieve current user details |
| POST | `/requests` | Create a stock request |
| GET | `/requests` | Retrieve stock requests |
| GET | `/requests/{id}` | Retrieve a specific request |
| POST | `/requests/{id}/approve` | Approve a pending request (manager only) |
| POST | `/requests/{id}/reject` | Reject a pending request (manager only) |
| GET | `/requests/{id}/audit` | Retrieve request audit history |

Interactive API documentation is available at:

`http://127.0.0.1:8000/docs`

## Project Setup

### 1. Clone the repository

```bash
git clone https://github.com/AfreenTaj17/retail-operations-automation.git
cd retail-operations-automation
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the JWT secret

In PowerShell, generate a secret for your local development session:

```powershell
$env:JWT_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Keep this secret private. Use the same PowerShell session when starting the backend.

### 5. Start the FastAPI backend

```bash
uvicorn main:app --reload
```

The backend will be available at:

`http://127.0.0.1:8000`

### 6. Create a manager account

Open a second terminal, activate the virtual environment, and run:

```bash
python create_manager.py
```

Follow the prompts to create a manager account.

Employee accounts can be registered through the application's registration API.

### 7. Start the Streamlit frontend

Open another terminal, activate the virtual environment, and run:

```bash
streamlit run frontend.py
```

The application will open in your browser.

## Running Automated Tests

Run the test suite with:

```bash
pytest -v
```

The current test suite contains 12 tests covering:

- Employee authentication
- Invalid login credentials
- JWT-based user identification
- Unauthenticated API access
- Stock request creation
- Input validation
- Request not found
- Employee permission restrictions
- Manager approval
- Audit history
- Duplicate approval prevention
- Request rejection and status validation

**Latest local test result: 12 passed.**

## Continuous Integration

GitHub Actions is configured in:

`.github/workflows/ci.yml`

The workflow runs when code is pushed to `main` or a pull request targets `main`.

It automatically:

1. Checks out the repository.
2. Sets up Python 3.12.
3. Installs project dependencies.
4. Runs the Pytest suite.

[View GitHub Actions](https://github.com/AfreenTaj17/retail-operations-automation/actions)

## Security Considerations

- Passwords are stored as Argon2 hashes, not plaintext.
- JWTs are used to authenticate protected API requests.
- Manager-only operations are protected by role-based authorization.
- SQL queries use parameterized statements.
- The JWT signing secret is supplied through an environment variable.
- Local databases, virtual environments, and `.env` files are excluded through `.gitignore`.

This project is a learning and portfolio prototype. Production deployment would require additional security hardening, secret management, HTTPS, database deployment planning, monitoring, and token lifecycle controls.

## Future Improvements

- Password reset functionality.
- Refresh-token and session-management improvements.
- More extensive automated tests.
- Deployment to a cloud platform.
- Enhanced dashboard analytics.
- More detailed audit reporting.

## Author

**Afreen Taj**

MCA – Data Science | Python | SQL | Machine Learning | Backend Development

- GitHub: [AfreenTaj17](https://github.com/AfreenTaj17)
- LinkedIn: [Afreen Taj](https://www.linkedin.com/in/afreentaj17/)

---

*Built as an independent portfolio project to demonstrate backend development, API design, authentication, database integration, workflow automation, testing, and CI/CD fundamentals.*
