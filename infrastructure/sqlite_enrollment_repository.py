import sqlite3


class EnrollmentRepository:
    """Encapsulates all SQLite access for the `enrollments` table.

    This class owns the database connection lifecycle, schema creation,
    the current-enrolled-credits lookup, and persistence of enrollment
    results. It reproduces the exact SQL and behavior that previously
    lived inline in legacy_enrollment_processor.py's run_legacy_enrollment().

    It has no knowledge of CSV parsing, business rules (credit limits,
    prerequisites, Dean overrides), HTML report generation, or
    notification messages.
    """

    def __init__(self, db_path):
        self._conn = sqlite3.connect(db_path)
        self._cursor = self._conn.cursor()

    def create_schema(self):
        """Create the enrollments table if it does not already exist.

        Preserves the exact schema from the legacy program:
        (student_id TEXT, student_name TEXT, course_code TEXT,
         credits INTEGER, status TEXT)
        """
        self._cursor.execute('''CREATE TABLE IF NOT EXISTS enrollments
                          (student_id TEXT, student_name TEXT, course_code TEXT, credits INTEGER, status TEXT)''')

    def get_current_enrolled_credits(self, student_id):
        """Return the sum of credits for this student's ENROLLED rows.

        Preserves the exact query and the legacy "0 if no result" fallback.
        """
        self._cursor.execute(
            "SELECT SUM(credits) FROM enrollments WHERE student_id=? AND status='ENROLLED'",
            (student_id,)
        )
        result = self._cursor.fetchone()[0]
        return result if result else 0

    def save_result(self, student_id, student_name, course_code, credits, status):
        """Insert one enrollment result row.

        Preserves the exact positional INSERT used by the legacy program.
        """
        self._cursor.execute(
            "INSERT INTO enrollments VALUES (?, ?, ?, ?, ?)",
            (student_id, student_name, course_code, credits, status)
        )

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()
