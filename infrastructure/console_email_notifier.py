def send_notification(message):
    """Send a notification message.

    For now this "sends an email" the same way the legacy program did:
    by printing the message to the console. Reproduces the exact side
    effect that previously lived inline as print(f"SENDING EMAIL TO: ...")
    calls in each business-rule branch (originally
    legacy_enrollment_processor.py:51,55,59,62).

    This function has no knowledge of *what* the message says or *why*
    it is being sent -- it does not know about enrollment status, credit
    limits, prerequisites, Dean overrides, SQLite, CSV parsing, or HTML.
    It only knows how to deliver a string it is handed.
    """
    print(message)
