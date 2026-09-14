import os
import csv


def read_enrollment_rows(csv_path):
    """Read and parse enrollment request rows from a CSV file.

    Reproduces the exact file-existence check, header skip, and per-row
    parsing/type-conversion that previously lived inline in main.py
    (originally legacy_enrollment_processor.py:23-38).

    Returns:
        None if the file at `csv_path` does not exist -- the caller is
        expected to reproduce the legacy "ERROR: CSV file not found!"
        message and early return in that case.

        Otherwise, a list of tuples, one per data row (header excluded),
        each shaped as:
            (student_id, student_name, course_code, credits,
             has_prereqs, override_code)
        where `credits` is an int and `has_prereqs` is a bool, matching
        the legacy int(row[3]) and row[4].strip().lower() == 'true'
        conversions exactly.

    This function has no knowledge of SQLite, credit-limit/prerequisite/
    override rules, enrollment status, HTML rendering, or notifications --
    it only turns CSV text into parsed rows.
    """
    if not os.path.exists(csv_path):
        return None

    rows = []
    with open(csv_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header

        for row in reader:
            student_id = row[0]
            student_name = row[1]
            course_code = row[2]
            credits = int(row[3])
            has_prereqs = row[4].strip().lower() == 'true'
            override_code = row[5]

            rows.append((student_id, student_name, course_code, credits, has_prereqs, override_code))

    return rows
