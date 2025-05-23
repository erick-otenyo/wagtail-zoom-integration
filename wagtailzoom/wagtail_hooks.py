from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from modelcluster.models import get_all_child_relations
from wagtail import hooks
from wagtail.admin import messages
from wagtail.admin import widgets as wagtail_admin_widgets
from wagtail.contrib.forms.models import AbstractFormField

from .views import zoom_integration_view


@hooks.register('register_admin_urls')
def urlconf_wagtail_zoom():
    return [
        path('zoom-integration/<int:page_id>', zoom_integration_view, name="zoom_integration_view"),
    ]


@hooks.register('register_page_listing_buttons')
def page_listing_buttons(page, user, next_url=None):
    if hasattr(page, "is_zoom_integration") and hasattr(page, "zoom_event"):
        latest_revision = page.get_latest_revision_as_object()
        if latest_revision.zoom_event_id and page.show_page_listing_zoom_integration_button():
            url = reverse("zoom_integration_view", args=[page.pk, ])
            yield wagtail_admin_widgets.ListingButton(
                "Zoom Integration",
                url,
                priority=50
            )


@hooks.register('after_publish_page')
def show_zoom_integration_fields_warning(request, page):
    if hasattr(page, "is_zoom_integration") and hasattr(page, "zoom_event"):
        form_fields_changed = False
        
        if page.zoom_event_id:
            if page.zoom_reg_fields_mapping:
                form_fields_rel_name = None
                # get form fields relation name
                relations = get_all_child_relations(page)
                for relation in relations:
                    related_name = relation.related_name
                    rels = getattr(page, related_name)
                    # check if is instance of AbstractFormField
                    if isinstance(rels.first(), AbstractFormField):
                        form_fields_rel_name = related_name
                        break
                
                if form_fields_rel_name and hasattr(page, form_fields_rel_name):
                    form_fields = getattr(page, form_fields_rel_name).all()
                    
                    form_fields_names = []
                    merge_field_names = []
                    
                    for form_field in form_fields:
                        form_fields_names.append(form_field.clean_name)
                    
                    for key, value in page.zoom_merge_fields.items():
                        merge_field_names.append(value)
                    
                    for merge_field_name in merge_field_names:
                        if merge_field_name not in form_fields_names:
                            page.zoom_reg_fields_mapping = ""
                            page.save()
                            form_fields_changed = True
                            break
            
            if not page.zoom_merge_fields:
                url = reverse("zoom_integration_view", args=[page.pk, ])
                message = _(
                    f"A zoom event is set for the page '{page.title}', "
                    f"but Zoom integration fields have not been set up. Please set up zoom integration fields as well")
                
                if form_fields_changed:
                    message = _(f"Form fields were changed for page '{page.title}'. "
                                f"Please update Zoom integration fields as well.")
                
                buttons = [messages.button(url, _("Zoom Integration"), )]
                
                messages.warning(request, _(message), buttons=buttons)
