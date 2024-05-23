import json

from django.forms.widgets import Input, Select
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from requests import HTTPError
from wagtail.models import Site

from .api import ZoomApi
from .errors import ZoomApiCredentialsError


class CustomSelect(Select):
    def create_option(self, *args, **kwargs):
        option = super().create_option(*args, **kwargs)
        if not option.get('value'):
            option['attrs']['disabled'] = True

        return option


class ZoomEventSelectWidget(Input):
    template_name = "wagtailzoom/widgets/zoom_event_select_widget.html"
    js_template_name = "wagtailzoom/widgets/zoom_event_select_widget_js.html"

    def get_context(self, name, value, attrs):
        ctx = super(ZoomEventSelectWidget, self).get_context(name, value, attrs)

        zoom_error = None

        json_value = self.get_json_value(value)
        event_id = json_value.get("event_id")
        zoom_events = []

        try:
            zoom_events = self.get_zoom_events()
        except ZoomApiCredentialsError as e:
            zoom_error = e.message
        except Exception as e:
            zoom_error = _("Error obtaining Zoom events. "
                           "Please make sure the Zoom credentials in Zoom Settings are correct, "
                           "and have required Zoom Account access scope.")

            if isinstance(e, HTTPError):
                response = e.response.json()
                if response and response.get("message"):
                    zoom_error += _("- Specific Error: ") + response.get("message")

        ctx["widget"]["value"] = json.dumps(json_value)
        ctx['widget']['extra_js'] = self.render_js(name, event_id, zoom_events)
        ctx["widget"]["selectable_events"] = zoom_events
        ctx["widget"]["stored_event_id"] = event_id
        ctx["widget"]["zoom_error"] = zoom_error
        ctx["widget"]["no_events_message"] = _("No Upcoming or Ongoing Meetings/Webinars found. "
                                               "Please create one on Zoom and try again.")

        return ctx

    def render_js(self, name, event_id, zoom_events):
        ctx = {
            "widget_name": name,
            "widget_js_name": name.replace('-', '_'),
            "stored_event_id": event_id,
            "selectable_events": zoom_events
        }

        return render_to_string(self.js_template_name, ctx)

    def get_json_value(self, value):
        if value:
            json_value = json.loads(value)
        else:
            json_value = json.loads('{}')

        if "event_id" not in json_value:
            json_value['event_id'] = ""
        if "event_type" not in json_value:
            json_value['event_type'] = ""
        if "event_topic" not in json_value:
            json_value['event_topic'] = ""

        return json_value

    def get_zoom_events(self):
        from .models import ZoomSettings

        current_site = Site.objects.get(is_default_site=True)

        zoom_settings = ZoomSettings.for_site(current_site)
        api = ZoomApi(zoom_settings.oauth_account_id, zoom_settings.oauth_client_id,
                      zoom_settings.oauth_client_secret)
        events = api.get_events()

        return events
