import datetime
import json

import requests

from validation import check_no_pii

REAL_URL = "https://www.google-analytics.com/mp/collect"
DEBUG_URL = "https://www.google-analytics.com/debug/mp/collect"


def _log(signup_id, event_name, params, status, timestamp_micros=None):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    shown_params = {k: v for k, v in params.items() if k != "signup_id"}
    backdated = ""
    if timestamp_micros is not None:
        event_dt = datetime.datetime.fromtimestamp(timestamp_micros / 1_000_000, tz=datetime.timezone.utc)
        backdated = f" ga4_timestamp={event_dt.isoformat(timespec='seconds')}"
    print(f"[{ts}] signup_id={signup_id} event={event_name} params={shown_params} status={status}{backdated}")


class GA4Client:
    def __init__(self, measurement_id, api_secret, dry_run=False, validate=False):
        self.measurement_id = measurement_id
        self.api_secret = api_secret
        self.dry_run = dry_run
        self.validate = validate
        self.session = requests.Session()

    def send(self, client_id, event, timestamp_micros=None):
        signup_id = event["params"]["signup_id"]
        name = event["name"]
        params = event["params"]

        violations = check_no_pii(params)
        if violations:
            _log(signup_id, name, params, "REJECTED (PII check failed)")
            for v in violations:
                print(f"    PII violation: {v}")
            return None

        payload = {
            "client_id": client_id,
            "events": [{"name": event["name"], "params": event["params"]}],
        }
        if timestamp_micros is not None:
            payload["timestamp_micros"] = timestamp_micros

        if self.validate:
            resp = self.session.post(
                DEBUG_URL,
                params={"measurement_id": self.measurement_id, "api_secret": self.api_secret},
                data=json.dumps(payload),
            )
            status = f"VALIDATE http={resp.status_code}"
            _log(signup_id, name, params, status, timestamp_micros)
            print(f"    payload={json.dumps(payload)}")
            try:
                print(f"    validation_response={resp.json()}")
            except ValueError:
                print(f"    validation_response=<non-JSON body: {resp.text!r}>")
            return resp

        if self.dry_run:
            _log(signup_id, name, params, "DRY-RUN (not sent)", timestamp_micros)
            print(f"    payload={json.dumps(payload)}")
            return None

        resp = self.session.post(
            REAL_URL,
            params={"measurement_id": self.measurement_id, "api_secret": self.api_secret},
            data=json.dumps(payload),
        )
        _log(signup_id, name, params, resp.status_code, timestamp_micros)
        return resp
