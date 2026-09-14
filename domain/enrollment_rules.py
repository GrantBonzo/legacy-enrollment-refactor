MAX_CREDITS = 18
DEAN_OVERRIDE_CODE = "DEAN_APPROVED"


def determine_status(current_enrolled_credits, credits, has_prereqs, override_code):
    """Determine the enrollment status for a single request.

    Reproduces the exact nested decision logic that previously lived
    inline in main.py (originally legacy_enrollment_processor.py:48-62):

        1. If adding `credits` to `current_enrolled_credits` would exceed
           MAX_CREDITS -> "FAILED - CREDIT LIMIT EXCEEDED".
        2. Otherwise, if prerequisites are met -> "ENROLLED".
        3. Otherwise, if `override_code` is DEAN_OVERRIDE_CODE ->
           "ENROLLED (OVERRIDE)".
        4. Otherwise -> "FAILED - MISSING PREREQS".

    This is a pure function: it takes plain values in and returns only a
    status string, with no side effects. It has no knowledge of SQLite,
    CSV parsing, notification messages, or HTML -- it doesn't know how
    `current_enrolled_credits` was obtained or what will happen with the
    status it returns.
    """
    if current_enrolled_credits + credits > MAX_CREDITS:
        return "FAILED - CREDIT LIMIT EXCEEDED"

    if has_prereqs:
        return "ENROLLED"

    if override_code == DEAN_OVERRIDE_CODE:
        return "ENROLLED (OVERRIDE)"

    return "FAILED - MISSING PREREQS"
