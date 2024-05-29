import json

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from modelcluster.models import get_all_child_relations
from requests import HTTPError
from wagtail.contrib.forms.models import AbstractFormField
from wagtail.models import Page

from .api import ZoomApi
from .errors import ZoomApiCredentialsError
from .forms import ZoomIntegrationForm
from .models import ZoomSettings


def zoom_integration_view(request, page_id):
    page = Page.objects.get(pk=page_id)
    form_page = page.get_latest_revision_as_object()
    edit_url = reverse("wagtailadmin_pages:edit", args=[form_page.pk])
    context = {"page": form_page, "page_edit_url": edit_url}
    template_name = "wagtailzoom/zoom_integration_form.html"

    parent_page = form_page.get_parent()
    explore_url = reverse("wagtailadmin_explore", args=[parent_page.id])

    if form_page.zoom_event:
        zoom_event_db = json.loads(form_page.zoom_event)
        event_id = zoom_event_db.get("event_id", None)
        event_type = zoom_event_db.get("event_type", None)

        if event_id:
            try:
                zoom_settings = ZoomSettings.for_request(request)
                zoom_api = ZoomApi(zoom_settings.oauth_account_id, zoom_settings.oauth_client_id,
                                   zoom_settings.oauth_client_secret)

                if event_type == "meeting":
                    zoom_event = zoom_api.get_meeting(event_id)
                else:
                    zoom_event = zoom_api.get_webinar(event_id)

                if zoom_event:

                    approval_type = zoom_event.get("settings", {}).get("approval_type")
                    context.update({"zoom_event": zoom_event})

                    if approval_type == 2:
                        topic = zoom_event.get("topic")
                        context.update({
                            "zoom_error": _(
                                "Registration is not enabled for the event '%(topic)s'. Please enable registration "
                                "for this event in your Zoom Account and try again") % {"topic": topic}})

            except ZoomApiCredentialsError as e:
                context.update({"zoom_error": e.message})
            except Exception as e:
                error_message = _("Error obtaining Zoom event.")

                if isinstance(e, HTTPError):
                    json_response = e.response.json()
                    if json_response and json_response.get("message"):
                        message = json_response.get("message")
                        error_message = f"{error_message} {message}"
                else:
                    message = _("Please make sure the Zoom credentials in Zoom Settings are correct and have required "
                                "Zoom Account access scope")
                    error_message = f"{error_message}  {message}"

                context.update({"zoom_error": error_message})

    if context.get("zoom_error"):
        return render(request, template_name, context=context)

    form_fields_rel_name = None
    # get form fields relation name
    relations = get_all_child_relations(form_page)
    for relation in relations:
        related_name = relation.related_name
        rels = getattr(form_page, related_name)
        # check if is instance of AbstractFormField
        if isinstance(rels.first(), AbstractFormField):
            form_fields_rel_name = related_name
            break

    form_fields = None
    has_form_fields = False

    if form_fields_rel_name and hasattr(form_page, form_fields_rel_name):
        form_fields = getattr(form_page, form_fields_rel_name).all()

    if form_fields is not None:
        has_form_fields = True

    context.update({"has_form_fields": has_form_fields})

    if request.method == 'POST':
        form = ZoomIntegrationForm(form_fields=form_fields, data=request.POST)

        if form.is_valid():
            merge_fields_data = json.dumps(form.cleaned_data)
            form_page.zoom_reg_fields_mapping = merge_fields_data
            form_page.save()

            return HttpResponseRedirect(explore_url)
        else:
            context.update({"form": form})
            return render(request, template_name, context=context)

    initial_data = None

    if form_page.zoom_reg_fields_mapping:
        initial_data = json.loads(form_page.zoom_reg_fields_mapping)

    form = ZoomIntegrationForm(form_fields=form_fields, initial=initial_data)
    context.update({"form": form})

    return render(request, template_name, context=context)
