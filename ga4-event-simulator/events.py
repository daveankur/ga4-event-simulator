EVENT_SEQUENCE = [
    "signup_page_viewed",
    "signup_step1_submitted",
    "signup_step2_submitted",
    "signup_verification",
    "signup_completed",
]

PAGE_URLS = {
    "signup_page_viewed": "#/signup",
    "signup_step1_submitted": "#/signup/step1",
    "signup_step2_submitted": "#/signup/step2",
    "signup_verification": "#/signup/verify",
    "signup_completed": "#/signup/complete",
}


def build_event(name, signup_id, profile, account_id=None):
    params = {
        "signup_id": signup_id,
        "source_feature": "signup",
        "page_url": PAGE_URLS[name],
        # Measurement Protocol events are invisible in GA4 DebugView unless
        # flagged this way; they still flow into standard reports/BigQuery.
        # engagement_time_msec must accompany debug_mode per Google's docs.
        "debug_mode": True,
        "engagement_time_msec": 100,
    }

    if name == "signup_step1_submitted":
        params["signup_method"] = profile["signup_method"]
        params["email_domain"] = profile["email_domain"]
    elif name == "signup_step2_submitted":
        params["setup_option"] = profile["setup_option"]
        params["data_center"] = profile["data_center"]
    elif name == "signup_completed":
        params["account_id"] = account_id

    return {"name": name, "params": params}
