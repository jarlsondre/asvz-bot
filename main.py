import requests
import time
import os
from datetime import datetime, timezone

# Configuration
LESSON_ID = "694773"
BEARER_TOKEN = None

MAX_RETRY_DURATION = 5  # Try for at most 5 seconds


def get_lesson_info(lesson_id):
    """Fetch lesson information including enrollment start time."""
    url = f"https://schalter.asvz.ch/tn-api/api/Lessons/{lesson_id}"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch lesson info: {response.status_code}")

    data = response.json()
    return data["data"]


def enroll_in_lesson(lesson_id, bearer_token, attempt_num):
    """Attempt to enroll in a lesson."""
    url = f"https://schalter.asvz.ch/tn-api/api/Lessons/{lesson_id}/Enrollment"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:143.0) Gecko/20100101 Firefox/143.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Origin": "https://schalter.asvz.ch",
        "Referer": f"https://schalter.asvz.ch/tn/lessons/{lesson_id}",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    data = {}
    request_time = get_timestamp()
    print(f"[{request_time}] Attempt {attempt_num}: Sent")

    try:
        response = requests.post(url, headers=headers, json=data)
        response_time = get_timestamp()

        print(f"[{response_time}] Attempt {attempt_num}: Status {response.status_code}")

        if response.status_code == 201:
            print(f"[{response_time}] ✓ SUCCESS! Enrolled in lesson!")
            print(f"Response: {response.text}")
            return True
        else:
            try:
                error_data = response.json()
                if "errors" in error_data and error_data["errors"]:
                    print(f"  → {error_data['errors'][0]['message']}")
            except (ValueError, KeyError):
                print(f"  → Response: {response.text}")
            return False
    except Exception as e:
        print(f"[{get_timestamp()}] Attempt {attempt_num}: Error - {e}")
        return False


def get_timestamp():
    """Get current timestamp as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def log_with_timestamp(message):
    """Print a message with timestamp prefix."""
    print(f"[{get_timestamp()}] {message}")


def get_config():
    """Get lesson ID and bearer token from config, environment, or user input."""
    lesson_id = LESSON_ID
    if lesson_id is None:
        lesson_id = input("Enter lesson ID: ").strip()

    bearer_token = BEARER_TOKEN or os.environ.get("ASVZ_TOKEN")
    if bearer_token is None:
        bearer_token = input("Enter bearer token: ").strip()

    return lesson_id, bearer_token


def display_lesson_info(lesson_info):
    """Display lesson information to the user."""
    print(f"Sport: {lesson_info['sportName']}")
    print(f"Title: {lesson_info['title']}")
    print(f"Enrollment opens: {lesson_info['enrollmentFrom']}")
    print(
        f"Participants: {lesson_info['participantCount']}/{lesson_info['participantsMax']}\n"
    )


def retry_enrollment(lesson_id, bearer_token, max_duration):
    """Retry enrollment attempts until successful or max duration exceeded."""
    start_time = time.time()
    end_time = start_time + max_duration

    log_with_timestamp(f"Starting enrollment attempts (max {max_duration}s)...\n")

    attempt = 0
    while time.time() < end_time:
        attempt += 1
        if enroll_in_lesson(lesson_id, bearer_token, attempt):
            return True

    return False


def main():
    # Get configuration
    lesson_id, bearer_token = get_config()

    log_with_timestamp(f"Fetching lesson info for ID: {lesson_id}")
    lesson_info = get_lesson_info(lesson_id)

    enrollment_from_str = lesson_info["enrollmentFrom"]
    enrollment_from_utc = datetime.fromisoformat(enrollment_from_str).astimezone(
        timezone.utc
    )

    display_lesson_info(lesson_info)

    # Wait until enrollment opens
    now = datetime.now(timezone.utc)
    wait_time = (enrollment_from_utc - now).total_seconds()

    if wait_time > 0:
        log_with_timestamp(
            f"\nWaiting {wait_time:.1f} seconds until enrollment opens..."
        )
        time.sleep(wait_time)
    else:
        log_with_timestamp("\nEnrollment window already open, starting immediately...")

    enrollment_success = retry_enrollment(lesson_id, bearer_token, MAX_RETRY_DURATION)

    if enrollment_success:
        log_with_timestamp("\nEnrollment successful!")
    else:
        log_with_timestamp(f"\nFailed to enroll after {MAX_RETRY_DURATION}s.")


if __name__ == "__main__":
    main()
