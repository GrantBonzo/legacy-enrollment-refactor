def build_notification_message(student_name, course_code, status):
    """Build the notification message text for a given enrollment outcome.

    Reproduces the exact status-to-message mapping that previously lived
    inline in main.py as an if/elif/else dispatch (originally
    legacy_enrollment_processor.py:51,55,59,62).

    This is a pure function: it takes plain values in and returns only a
    message string, with no side effects. It does not decide the status
    itself (that's domain/enrollment_rules.py's job) and it does not send
    or print anything -- it only knows how to phrase the message for a
    status it's handed.
    """
    if status == "FAILED - CREDIT LIMIT EXCEEDED":
        return f"SENDING EMAIL TO: {student_name} -> Registration failed for {course_code} (Credit limit)."

    if status == "ENROLLED":
        return f"SENDING EMAIL TO: {student_name} -> Successfully enrolled in {course_code}."

    if status == "ENROLLED (OVERRIDE)":
        return f"SENDING EMAIL TO: {student_name} -> Enrolled in {course_code} with Dean override."

    return f"SENDING EMAIL TO: {student_name} -> Registration failed for {course_code} (Missing Prereqs)."
