import random
import uuid


def new_id():
    return str(uuid.uuid4())


def generate_profile(pools):
    return {
        "signup_method": random.choice(pools["signup_method"]),
        "email_domain": random.choice(pools["email_domain"]),
        "setup_option": random.choice(pools["setup_option"]),
        "data_center": random.choice(pools["data_center"]),
    }


def generate_account_id():
    return str(random.randint(10**9, 10**10 - 1))
