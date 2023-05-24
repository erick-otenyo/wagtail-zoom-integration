from django import forms

from .widgets import CustomSelect

ZOOM_EVENT_REGISTRATION_REQUIRED_FIELDS = [
    {"tag": "email", "name": "Email", "type": "email", "required": True, },
    {"tag": "first_name", "name": "First Name", "type": "text", "required": True},
    {"tag": "last_name", "name": "Last Name", "type": "text", "required": True},
]


class ZoomIntegrationForm(forms.Form):
    def __init__(self, form_fields=None, *args, **kwargs):
        # Initialize the form instance.
        super(ZoomIntegrationForm, self).__init__(*args, **kwargs)

        merge_fields = ZOOM_EVENT_REGISTRATION_REQUIRED_FIELDS

        if form_fields:
            for field in merge_fields:
                choices = [("", "-- Select field to merge--")]

                if field.get("type") == "email":
                    for form_field in form_fields:
                        if form_field.field_type == 'email':
                            choices.append((form_field.clean_name, form_field.label))
                elif field.get("type") == "number":
                    for form_field in form_fields:
                        if form_field.field_type == 'number':
                            choices.append((form_field.clean_name, form_field.label))
                elif field.get("type") == "url":
                    for form_field in form_fields:
                        if form_field.field_type == 'url':
                            choices.append((form_field.clean_name, form_field.label))
                elif field.get("type") == "radio":
                    for form_field in form_fields:
                        if form_field.field_type == 'radio':
                            choices.append((form_field.clean_name, form_field.label))
                elif field.get("type") == "dropdown":
                    for form_field in form_fields:
                        if form_field.field_type == 'dropdown':
                            choices.append((form_field.clean_name, form_field.label))
                elif field.get("type") == "checkboxes":
                    for form_field in form_fields:
                        if form_field.field_type == 'checkboxes':
                            choices.append((form_field.clean_name, form_field.label))
                elif field.get("type") == "date" or field.get("type") == "birthday":
                    for form_field in form_fields:
                        if form_field.field_type == 'date':
                            choices.append((form_field.clean_name, form_field.label))
                else:
                    for form_field in form_fields:
                        if form_field.field_type == 'singleline' or form_field.field_type == "multiline":
                            choices.append((form_field.clean_name, form_field.label))

                kwargs = {
                    'label': field.get('name', None),
                    'required': field.get('required', False)
                }

                name = field.get("tag")

                self.fields.update({name: forms.ChoiceField(choices=choices, widget=CustomSelect, **kwargs)})
                self.fields[name].label = field.get("name")
