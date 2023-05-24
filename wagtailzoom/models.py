import json

from django.core.mail import mail_admins
from django.db import models
from django.template import Context, Template
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.forms.models import AbstractForm
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.contrib.settings.registry import register_setting

from .api import ZoomApi
from .widgets import ZoomEventSelectWidget


@register_setting
class ZoomSettings(BaseSiteSetting):
    api_key = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name=_("Zoom API Key"),
        help_text=_("API Key obtained from Zoom"),
    )
    api_secret = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name=_("Zoom API Secret"),
        help_text=_("API Secret obtained from Zoom"),
    )

    panels = [
        FieldPanel("api_key"),
        FieldPanel("api_secret"),
    ]


class AbstractZoomIntegrationForm(AbstractForm):
    zoom_event = models.TextField(blank=True, null=True, verbose_name=_('Zoom Event'), help_text=_('Select Zoom Event'))

    zoom_reg_fields_mapping = models.TextField(blank=True, null=True)

    integration_panels = [
        FieldPanel("zoom_event", widget=ZoomEventSelectWidget),
    ]

    class Meta:
        abstract = True

    @property
    def zoom_event_id(self):
        return self.get_data().get("event_id")

    @property
    def zoom_event_type(self):
        return self.get_data().get("event_type")

    @property
    def zoom_merge_fields(self):
        return json.loads(self.zoom_reg_fields_mapping)

    def get_data(self):
        data = {}
        event = json.loads(self.zoom_event)
        if event:
            data.update({
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "event_topic": event.get("event_topic")
            })
        return data

    def format_zoom_form_submission(self, form):
        formatted_form_data = {}
        for k, v in form.cleaned_data.items():
            formatted_form_data[k.replace('-', '_')] = v
        return formatted_form_data

    def integration_operation(self, instance, **kwargs):
        success = False
        response = None
        request = kwargs.get('request', None)

        if self.zoom_event_id:
            zoom_settings = ZoomSettings.for_request(request)
            zoom = ZoomApi(api_key=zoom_settings.api_key, api_secret=zoom_settings.api_secret)

            rendered_dictionary = self.render_zoom_dictionary(
                self.format_zoom_form_submission(kwargs['form']),
            )

            try:
                dict_data = json.loads(rendered_dictionary)

                event_id = self.zoom_event_id

                # if meeting
                if self.zoom_event_type == "meeting":
                    response = zoom.add_meeting_registrant(event_id, dict_data)
                else:
                    response = zoom.add_webinar_registrant(event_id, dict_data)
                # mark as success
                success = True
            except Exception as e:
                # mark as failed
                success = False

                data = json.dumps(self.get_data())

                message = "Error \n {}\n  Rendered \n {}\n Zoom Form Data\n {}".format(str(e),
                                                                                       str(rendered_dictionary),
                                                                                       str(data))
                mail_admins(subject="Error when adding user to zoom event", message=message)

        return success, response

    def get_merge_fields_template(self):
        fields = self.zoom_merge_fields()
        for key, value in fields.items():
            if value:
                fields[key] = "{}{}{}".format("{{", value, "}}")
        return fields

    def render_zoom_dictionary(self, form_submission):

        merge_fields_templates = self.get_merge_fields_template()

        rendered_dictionary_template = json.dumps({
            **merge_fields_templates,
        })

        rendered_dictionary = Template(rendered_dictionary_template).render(Context(form_submission))
        return rendered_dictionary
