import base64

import iso8601
import requests

from wagtailzoom.errors import ZoomApiCredentialsError


def get_created_time(d):
    return iso8601.parse_date(d["created_at"])


class ZoomApi:
    def __init__(self, oauth_account_id, oauth_client_id, oauth_client_secret):
        self.is_active = False
        self.headers = {}
        self.base_url = "https://api.zoom.us/v2"

        if not oauth_account_id and not oauth_client_id and not oauth_client_secret:
            raise ZoomApiCredentialsError("Missing Zoom API OAUTH credentials")

        self.init_api(oauth_account_id, oauth_client_id, oauth_client_secret)

    def init_api(self, oauth_account_id, oauth_client_id, oauth_client_secret):
        auth_str = f"{oauth_client_id}:{oauth_client_secret}"
        encoded_auth_str = base64.b64encode(auth_str.encode()).decode('utf-8')

        r = requests.post(f'https://zoom.us/oauth/token?grant_type=account_credentials&account_id={oauth_account_id}',
                          headers={'Authorization': f'Basic {encoded_auth_str}'})

        r.raise_for_status()

        res = r.json()
        access_token = res.get("access_token")

        self.headers["Authorization"] = f"Bearer {access_token}"

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
        url = "{}/users/me/meetings?type=upcoming_meetings".format(self.base_url)
        response = self._get(url)
        response.raise_for_status()

        json_res = response.json()

        meetings = json_res.get("meetings", [])

        if meetings and limit > 1:
            meetings = meetings[:limit]
            meetings = sorted(meetings, key=get_created_time, reverse=True)

            for index, meeting in enumerate(meetings):
                meetings[index]["event_type"] = "meeting"
                meetings[index]["event_type_label"] = "Meeting"

        # sort by start time, with meeting closest to start  first
        if meetings:
            sorted(meetings, key=lambda x: x["start_time"]).reverse()

        return meetings

    def get_webinars(self, limit=10):
        url = "{}/users/me/webinars?type=upcoming".format(self.base_url)
        response = self._get(url)

        response.raise_for_status()

        json_res = response.json()
        webinars = json_res.get("webinars", [])

        if webinars and limit > 1:
            webinars = webinars[:limit]
            webinars = sorted(webinars, key=get_created_time, reverse=True)

            for index, webinar in enumerate(webinars):
                webinars[index]["event_type"] = "webinar"
                webinars[index]["event_type_label"] = "Webinar"

        # sort by start time, with webinar closest to start first
        if webinars:
            sorted(webinars, key=lambda x: x["start_time"]).reverse()

        return webinars

    def get_events(self):
        meetings = self.get_meetings(limit=20)

        try:
            webinars = self.get_webinars(limit=20)
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
