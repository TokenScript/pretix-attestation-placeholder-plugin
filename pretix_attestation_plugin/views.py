from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from pretix.control.views.event import EventSettingsViewMixin

from . import forms, models
from pretix.base.models import Order, OrderPosition

from .generator.java_generator_wrapper import get_private_key, get_public_key_in_hex, verify_magic_link, get_private_key_path, regenerate_att_link, order_position_attestation_link

import urllib.parse

import logging
logger = logging.getLogger(__name__)

class PluginSettingsView(EventSettingsViewMixin, FormView):
    form_class = forms.PluginSettingsForm
    template_name = 'pretix_attestation_plugin/attestation_plugin_settings.html'
    permission = 'can_change_event_settings'

    def get_context_data(self, **kwargs):
        kwargs["run_sign"] = self.request.build_absolute_uri("?validate_magic_links=1")
        kwargs["validation_result"] = "Unknown"
        regenerate = self.request.GET.get("regenerate_magic_links")

        if (self.request.GET.get("validate_magic_links")):
            valid_atts = 0
            invalid_atts = 0
            total_ops = 0
            regenerated_atts = 0
            try:
                current_event = self.request.event
                priv_key = get_private_key(event = current_event)
                public_key_in_hex = get_public_key_in_hex(priv_key = priv_key)
                path_to_key = get_private_key_path(current_event)

                orders = Order.objects.filter(event = current_event)
                ops = OrderPosition.objects.filter(order__in = orders)

                total_ops = ops.count()
                for op in ops:
                    att_is_valid = True
                    
                    try:
                        a = models.AttestationLink.objects.filter(order_position=op)
                        if not a.exists():
                            raise("No attestation for this ticket")
                        
                        magic_link_params = a[0].string_url
                        signature_ok = verify_magic_link(public_key_in_hex, magic_link_params)
                        if not signature_ok:
                            att_is_valid = False

                    except: 
                        att_is_valid = False

                    
                    if (not att_is_valid) and regenerate:

                        try:
                            regenerate_att_link(op, path_to_key)
                            attestation_link = order_position_attestation_link(op, "https://some.url", path_to_key)
                            parsed = urllib.parse.urlparse(attestation_link)
                            params = urllib.parse.parse_qs(parsed.query)
                            ticket_attestation = params['ticket'][0]

                            op.secret = ticket_attestation 
                            op.save()
                            att_is_valid = True
                            regenerated_atts += 1
                        except:
                            pass

                    if att_is_valid:
                        valid_atts += 1
                    else:
                        invalid_atts += 1
                                    
                regenerated_str = f", regenerated: {regenerated_atts}" if regenerate else ""
                kwargs["validation_result"] = f"Total tickets: {total_ops}, valid: {valid_atts}, invalid: {invalid_atts}{regenerated_str}"

                if invalid_atts > 0 and not regenerate:
                    kwargs["regenerate_atts_url"] = self.request.build_absolute_uri("?regenerate_magic_links=1&validate_magic_links=1")

            except: 
                kwargs["validation_result"] = "Can't read private key"

        return super().get_context_data(**kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs["current_base_url"] = models.BaseURL.objects.get(event=self.request.event).string_url
        except models.BaseURL.DoesNotExist:
            kwargs["current_base_url"] = "Not set yet"

        try:
            kwargs["upload"] = models.KeyFile.objects.get(event=self.request.event).upload
        except models.KeyFile.DoesNotExist:
            kwargs["upload"] = "Not uploaded yet"

        return kwargs

    def form_valid(self, form):
        self.write_to_file(form.cleaned_data["keyfile"])
        self.save_base_url(form.cleaned_data["base_url"])
        return super().form_valid(form)

    def write_to_file(self, cleaned_data):
        if(cleaned_data is None):
            return

        upload_data, num_bits = cleaned_data

        try:
            models.KeyFile.objects.update_or_create(
                event=self.request.event,
                defaults={"upload": upload_data}
            )
        except EnvironmentError:
            messages.error(self.request, _('We could not save your changes: Unable to save the file'))
            return

        messages.success(
            self.request,
            _(
                'Successfully uploaded .pem file. '
                'Number of bits {num_bits}'
            ).format(
                num_bits=num_bits
            ),
        )

    def save_base_url(self, base_url):
        if(base_url is None):
            return
        try:
            models.BaseURL.objects.update_or_create(
                event=self.request.event,
                defaults={"string_url": base_url},
            )
        except Exception:
            messages.error(self.request, _('We could not save your changes: Unable to update the url'))
            return

        messages.success(
            self.request,
            _(
                'Successfully changed the base URL '
                'Current base URL is {url}'
            ).format(
                url=base_url
            ),
        )

    def form_invalid(self, form):
        messages.error(self.request, _('We could not save your changes. See below for details.'))
        return super().form_invalid(form)

    def get_success_url(self, **kwargs):
        return reverse('plugins:pretix_attestation_plugin:attestation_plugin_settings', kwargs={
            'organizer': self.request.event.organizer.slug,
            'event': self.request.event.slug,
        })
