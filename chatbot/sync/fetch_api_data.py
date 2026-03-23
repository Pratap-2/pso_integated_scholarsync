import requests

EXAMS_API = "https://student-portal-2-gh1j.onrender.com/api/student/69abdbea843e1db183a2b20f/exam-schedule"
ASSIGNMENTS_API = "https://student-portal-2-gh1j.onrender.com/api/student/69abdbea843e1db183a2b20f/assignments"


def fetch_exam_schedule():

    r = requests.get(EXAMS_API)
    data = r.json()

    return data["data"]["examSchedules"]


def fetch_assignments():

    r = requests.get(ASSIGNMENTS_API)
    data = r.json()

    return data["data"]["assignments"]["upcoming"]