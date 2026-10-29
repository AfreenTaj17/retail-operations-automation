
import sqlite3

DATABASE_NAME = "retail.db"


def get_connection():
    """Open a database connection with foreign-key enforcement enabled."""
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create the required tables if they do not exist."""
    connection = get_connection()

    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS stock_requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending'
                    CHECK (status IN ('Pending', 'Approved', 'Rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id)
                    REFERENCES stock_requests(request_id)
            );
        """)
    finally:
        connection.close()


def create_stock_request(item, quantity, reason):
    """Save a request and its audit entry in one transaction."""
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO stock_requests (item, quantity, reason)
            VALUES (?, ?, ?)
            """,
            (item, quantity, reason),
        )
        request_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO audit_logs (request_id, action, details)
            VALUES (?, ?, ?)
            """,
            (request_id, "Created", f"Request created for {item}"),
        )

        connection.commit()
        return request_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_stock_request(request_id):
    """Retrieve one request by ID."""
    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT * FROM stock_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_all_stock_requests():
    """Retrieve all requests, newest first."""
    connection = get_connection()

    try:
        rows = connection.execute(
            "SELECT * FROM stock_requests ORDER BY request_id DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def update_request_status(request_id, new_status):
    """Approve or reject a pending request and record the action."""
    if new_status not in ("Approved", "Rejected"):
        raise ValueError("Status must be Approved or Rejected")

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE stock_requests
            SET status = ?
            WHERE request_id = ? AND status = 'Pending'
            """,
            (new_status, request_id),
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return False

        connection.execute(
            """
            INSERT INTO audit_logs (request_id, action, details)
            VALUES (?, ?, ?)
            """,
            (
                request_id,
                new_status,
                f"Request {new_status.lower()}",
            ),
        )

        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_audit_logs(request_id):
    """Retrieve audit history for one request."""
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT * FROM audit_logs
            WHERE request_id = ?
            ORDER BY log_id
            """,
            (request_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")

