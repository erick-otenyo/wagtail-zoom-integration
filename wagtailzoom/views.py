import json

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from modelcluster.models import get_all_child_relations
from wagtail.contrib.forms.models import AbstractFormField
from wagtail.models import Page

from .forms import ZoomIntegrationForm


def zoom_integration_view(request, page_id):
    page = Page.objects.get(pk=page_id)
    form_page = page.specific
    edit_url = reverse("wagtailadmin_pages:edit", args=[form_page.pk])
    context = {"page": form_page, "page_edit_url": edit_url}
    template_name = "wagtailzoom/zoom_integration_form.html"

    parent_page = form_page.get_parent()
    explore_url = reverse("wagtailadmin_explore", args=[parent_page.id])

    if form_page.zoom_event:
        context.update({"zoom_event": json.loads(form_page.zoom_event)})

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
