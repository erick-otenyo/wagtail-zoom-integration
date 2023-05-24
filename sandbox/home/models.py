from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import InlinePanel
from wagtail.contrib.forms.models import AbstractFormField
from wagtail.models import Page

from wagtailzoom.models import AbstractZoomIntegrationForm


class HomePage(Page):
    pass


class FormField(AbstractFormField):
    page = ParentalKey('EventRegistrationPage', on_delete=models.CASCADE, related_name='form_fields')


class EventRegistrationPage(AbstractZoomIntegrationForm):
    parent_pages = ["home.HomePage"]
    template = 'integration/event_registration_page.html'
    landing_page_template = 'integration/form_thank_you_landing.html'

    content_panels = Page.content_panels + AbstractZoomIntegrationForm.integration_panels + [
        InlinePanel('form_fields', label="Form fields"),
    ]
