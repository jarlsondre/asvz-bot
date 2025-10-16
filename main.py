import requests
import time
import os
from datetime import datetime, timedelta, timezone

# Configuration
LESSON_ID = None
BEARER_TOKEN = None

POLL_INTERVAL = 0.2  # 200ms between requests
START_BEFORE_SECONDS = 5  # Start polling 5 seconds before enrollment opens


def get_lesson_info(lesson_id):
    """Fetch lesson information including enrollment start time."""
    url = f"https://schalter.asvz.ch/tn-api/api/Lessons/{lesson_id}"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch lesson info: {response.status_code}")

    data = response.json()
    return data["data"]


def enroll_in_lesson(lesson_id, bearer_token):
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
    response = requests.post(url, headers=headers, json=data)
    return response


def main():
    # Get lesson ID
    lesson_id = LESSON_ID
    if lesson_id is None:
        lesson_id = input("Enter lesson ID: ").strip()
    
    # Get bearer token
    bearer_token = BEARER_TOKEN
    if bearer_token is None:
        bearer_token = os.environ.get("ASVZ_TOKEN")
    if bearer_token is None:
        bearer_token = input("Enter bearer token: ").strip()
    
    print(f"\nFetching lesson info for ID: {lesson_id}")
    lesson_info = get_lesson_info(lesson_id)

    enrollment_from_str = lesson_info["enrollmentFrom"]
    enrollment_from_utc = datetime.fromisoformat(enrollment_from_str).astimezone(
        timezone.utc
    )

    print(f"Sport: {lesson_info['sportName']}")
    print(f"Title: {lesson_info['title']}")
    print(f"Enrollment opens: {enrollment_from_str}")
    print(
        f"Participants: {lesson_info['participantCount']}/{lesson_info['participantsMax']}"
    )

    # Calculate when to start polling
    now = datetime.now(timezone.utc)
    start_polling_at = enrollment_from_utc - timedelta(seconds=START_BEFORE_SECONDS)
    
    wait_time = (start_polling_at - now).total_seconds()

    if wait_time > 0:
        print(f"\nWaiting {wait_time:.1f} seconds until polling starts...")
        time.sleep(wait_time)
    else:
        print(
            f"\nEnrollment window already open or opening soon, starting immediately..."
        )

    print(f"\nStarting enrollment attempts (every {int(POLL_INTERVAL * 1000)}ms)...")
    attempt = 0

    while True:
        attempt += 1
        response = enroll_in_lesson(lesson_id, bearer_token)

        print(f"Attempt {attempt}: Status {response.status_code}")

        if response.status_code == 201:
            print("\n✓ SUCCESS! Enrolled in lesson!")
            print(f"Response: {response.text}")
            break
        elif response.status_code == 422:
            # Still too early or validation error
            try:
                error_data = response.json()
                if "errors" in error_data and error_data["errors"]:
                    print(f"  → {error_data['errors'][0]['message']}")
            except:
                print(f"  → Response: {response.text}")
        else:
            print(f"  → Response: {response.text}")
            # Consider stopping after too many failed attempts with unexpected errors
            if attempt > 100:
                print("\nToo many attempts with errors. Stopping.")
                break

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
