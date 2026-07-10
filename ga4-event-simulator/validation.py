import re

EMAIL_LIKE = re.compile(r"@")


def check_no_pii(params):
    """Returns a list of violation descriptions; empty list means clean.

    Basic safety net per PRD 5.6: any field other than email_domain that
    contains an '@' looks like it might be a full email address, not the
    fake domain-only values this tool is supposed to generate.
    """
    violations = []
    for key, value in params.items():
        if key == "email_domain":
            continue
        if isinstance(value, str) and EMAIL_LIKE.search(value):
            violations.append(f"field '{key}' looks like it contains an email address: {value!r}")
    return violations
