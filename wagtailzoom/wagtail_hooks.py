from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin import widgets as wagtail_admin_widgets

from .models import AbstractZoomIntegrationForm
from .views import zoom_integration_view


@hooks.register('register_admin_urls')
def urlconf_wagtail_zoom():
    return [
        path('zoom-integration/<int:page_id>', zoom_integration_view, name="zoom_integration_view"),
    ]


@hooks.register('register_page_listing_buttons')
def page_listing_buttons(page, page_perms, next_url=None):
    if isinstance(page, AbstractZoomIntegrationForm):
        if page.zoom_event_id:
            url = reverse("zoom_integration_view", args=[page.pk, ])
            yield wagtail_admin_widgets.PageListingButton(
                "Zoom Integration",
                url,
                priority=40
            )
