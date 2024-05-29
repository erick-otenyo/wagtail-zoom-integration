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
    oauth_account_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name=_("Zoom OAUTH Account ID"),
        help_text=_("Account ID obtained from Zoom Server-to-Server OAuth"),
    )
    oauth_client_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name=_("Zoom OAUTH Client ID"),
        help_text=_("Client ID obtained from Zoom Server-to-Server OAuth"),
    )
    oauth_client_secret = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name=_("Zoom OAUTH Client Secret"),
        help_text=_("Client Secret obtained from Zoom Server-to-Server OAuth"),
    )

    panels = [
        FieldPanel("oauth_account_id"),
        FieldPanel("oauth_client_id"),
        FieldPanel("oauth_client_secret"),
    ]


class AbstractZoomIntegrationForm(AbstractForm):
    zoom_event = models.TextField(blank=True, null=True, verbose_name=_('Zoom Event'), help_text=_('Select Zoom Event'))
    zoom_reg_fields_mapping = models.TextField(blank=True, null=True)

    integration_panels = [
        FieldPanel("zoom_event", widget=ZoomEventSelectWidget),
    ]

    is_zoom_integration = True

    class Meta:
        abstract = True

    @property
    def zoom_event_id(self):
        return self.get_zoom_data().get("event_id")

    @property
    def zoom_event_type(self):
        return self.get_zoom_data().get("event_type")

    @property
    def zoom_merge_fields(self):
        if self.zoom_reg_fields_mapping:
            try:
                return json.loads(self.zoom_reg_fields_mapping)
            except Exception:
                pass
        return {}

    def get_zoom_data(self):
        data = {}
        if self.zoom_event:
            try:
                event = json.loads(self.zoom_event)

                if event:
                    data.update({
                        "event_id": event.get("event_id"),
                        "event_type": event.get("event_type"),
                        "event_topic": event.get("event_topic")
                    })
            except Exception:
                pass

        return data

    def should_perform_zoom_integration_operation(self, request, form):
        # override this method to add custom logic to determine if the zoom integration operation should be performed
        return True

    def show_page_listing_zoom_integration_button(self):
        # override this method to add custom logic to determine if the
        # zoom integration button should be shown in the page listing
        return True

    def process_form_submission(self, form):
        form_submission = super(AbstractZoomIntegrationForm, self).process_form_submission(form)

        if self.request and self.should_perform_zoom_integration_operation(self.request, form):
            self.zoom_integration_operation(self, form=form, request=self.request)

        return form_submission

    def serve(self, request, *args, **kwargs):
        # We need to access the request later on in integration operation
        self.request = request

        return super(AbstractZoomIntegrationForm, self).serve(request, *args, **kwargs)

    def format_zoom_form_submission(self, form):
        formatted_form_data = {}
        for k, v in form.cleaned_data.items():
            formatted_form_data[k.replace('-', '_')] = v
        return formatted_form_data

    def zoom_integration_operation(self, instance, **kwargs):
        success = False
        response = None
        request = kwargs.get('request', None)

        if self.zoom_event_id and self.zoom_merge_fields:
            try:
                zoom_settings = ZoomSettings.for_request(request)
                zoom = ZoomApi(zoom_settings.oauth_account_id, zoom_settings.oauth_client_id,
                               zoom_settings.oauth_client_secret)

                rendered_dictionary = self.render_zoom_dictionary(
                    self.format_zoom_form_submission(kwargs['form']),
                )
                dict_data = json.loads(rendered_dictionary)

                # check if meeting or webinar
                if self.zoom_event_type == "meeting":
                    response = zoom.add_meeting_registrant(self.zoom_event_id, dict_data)
                else:
                    response = zoom.add_webinar_registrant(self.zoom_event_id, dict_data)
                # mark as success
                success = True
            except Exception as e:
                # mark as failed
                success = False

                data = json.dumps(self.get_zoom_data())

                message = "Error \n {}\n  Rendered \n {}\n Zoom Form Data\n {}".format(str(e),
                                                                                       str(rendered_dictionary),
                                                                                       str(data))
                mail_admins(subject="Error adding user to zoom event", message=message)

        return success, response

    def get_zoom_fields_template(self):
        fields = self.zoom_merge_fields

        for key, value in fields.items():
            if value:
                fields[key] = "{}{}{}".format("{{", value, "}}")
        return fields

    def render_zoom_dictionary(self, form_submission):

        fields_templates = self.get_zoom_fields_template()

        rendered_dictionary_template = json.dumps({
            **fields_templates,
        })

        rendered_dictionary = Template(rendered_dictionary_template).render(Context(form_submission))
        return rendered_dictionary
