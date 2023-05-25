from datetime import datetime, timedelta
import iso8601

import jwt
import requests

from wagtailzoom.errors import ZoomApiCredentialsError

JWT_EXP_DELTA_SECONDS = 60 * 2  # 2 minutes


def get_created_time(d):
    return iso8601.parse_date(d["created_at"])


class ZoomApi:
    def __init__(self, api_key, api_secret):
        self.is_active = False
        self.headers = {}
        self.base_url = "https://api.zoom.us/v2"

        if not api_key:
            raise ZoomApiCredentialsError(
                "No Zoom API Key provided. Please set API Key from Zoom Settings under settings")

        if not api_secret:
            raise ZoomApiCredentialsError(
                "No Zoom API Secret provided. Please set API Secret from Zoom Settings under settings")

        self.init_api(api_key, api_secret)

    def init_api(self, api_key, api_secret):
        payload = {
            'iss': api_key,
            'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
        }

        jwt_token = jwt.encode(payload, api_secret)
        self.headers["Authorization"] = "Bearer {}".format(jwt_token)

        self.is_active = True

    def _get(self, url):
        headers = {**self.headers}

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response

    def _post(self, url, data):
        headers = {'Content-type': 'application/json', 'Accept': 'application/json', **self.headers}
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response

    def get_meetings(self, limit=10):
        url = "{}/users/me/meetings".format(self.base_url)
        response = self._get(url)
        response.raise_for_status()

        json_res = response.json()

        meetings = json_res.get("meetings", [])

        if meetings and limit > 1:
            meetings = meetings[:limit]
            meetings = sorted(meetings, key=get_created_time, reverse=True)

            for index, meeting in enumerate(meetings):
                meetings[index]["event_type"] = "meeting"

        return meetings

    def get_webinars(self, limit=10):
        url = "{}/users/me/webinars".format(self.base_url)
        response = self._get(url)

        response.raise_for_status()

        json_res = response.json()
        webinars = json_res.get("webinars", [])

        if webinars and limit > 1:
            webinars = webinars[:limit]
            webinars = sorted(webinars, key=get_created_time, reverse=True)

            for index, webinar in enumerate(webinars):
                webinars[index]["event_type"] = "webinar"

        return webinars

    def get_events(self):
        meetings = self.get_meetings(limit=5)

        try:
            webinars = self.get_webinars(limit=5)
            meetings.extend(webinars)
        except Exception as e:
            pass

        return meetings

    def get_meeting(self, meeting_id):
        url = "{}/meetings/{}".format(self.base_url, meeting_id)
        response = self._get(url)
        return response.json()

    def get_webinar(self, webinar_id):
        url = "{}/webinars/{}".format(self.base_url, webinar_id)
        response = self._get(url)
        return response.json()

    def get_meeting_questions(self, meeting_id):
        url = "{}/meetings/{}/registrants/questions".format(self.base_url, meeting_id)
        response = self._get(url)
        return response.json()

    def add_meeting_registrant(self, meeting_id, data):
        url = "{}/meetings/{}/registrants".format(self.base_url, meeting_id)
        response = self._post(url, data)
        return response.json()

    def add_webinar_registrant(self, webinar_id, data):
        url = "{}/webinars/{}/registrants".format(self.base_url, webinar_id)
        response = self._post(url, data)
        return response.json()


class ZoomEventsApi:
    def __init__(self):
        self.base_url = "https://events.zoom.us/api/v1"

    def _get(self, url, params=None):
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response

    def get_event_sessions(self, event_id):
        url = f"{self.base_url}/e/v/events/sessions"
        params = {"eventId": event_id}
        response = self._get(url, params)
        return response.json()

    def get_event_speakers(self, event_id):
        url = f"{self.base_url}/e/v/events/speakers"
        params = {"eventId": event_id}
        response = self._get(url, params)
        return response.json()

    def get_event_sponsors(self, event_id):
        url = f"{self.base_url}/e/v/events/sponsors"
        params = {"eventId": event_id}
        response = self._get(url, params)
        return response.json()
