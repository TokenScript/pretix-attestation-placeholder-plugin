from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from pretix.control.views.event import EventSettingsViewMixin

from . import forms, models
from pretix.base.models import Order, OrderPosition

import asn1

import urllib.parse

from .models import (
    KeyFile,
)

from os import path

from OpenSSL import crypto

import base64

import eth_keys

def get_public_key_in_hex(event):
    key_data = None
    priv_key = None

    path_to_key = KeyFile.objects.get(event=event).upload.path

    if not path.isfile(path_to_key):
        raise ValueError(f'Key file not found in {path_to_key}')
    with open(path_to_key, 'r') as file:
        key_data = file.read()

    priv_key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_data)
    pub_key_data = priv_key.to_cryptography_key().public_key().public_numbers()

    x_bytes = pub_key_data.x.to_bytes(32, 'big')
    y_bytes = pub_key_data.y.to_bytes(32, 'big')

    return "0x" + ''.join('{:02x}'.format(x) for x in (x_bytes+y_bytes))


def verify_magic_link(public_key_in_hex, magic_link_params):
    parsed = urllib.parse.urlparse(magic_link_params)
    params = urllib.parse.parse_qs(parsed.query)

    ticket_attestation = params['ticket'][0]

    ticketbytes = base64.urlsafe_b64decode(ticket_attestation + '=' * (4 - len(ticket_attestation) % 4))

    # read ticket sequence
    decoder = asn1.Decoder()
    decoder.start(ticketbytes)
    tag, value = decoder.read()

    # read ticket body and signature from prev sequence content
    decoder.start(value)
    tag, value = decoder.read()
    # wrap in sequence
    ticket_body = b'\x30'+bytes([len(value)])+value

    tag, value = decoder.read()
    ticket_signature = bytearray(value)
    # have to replace last byte 1b -> 00 1c -> 01
    if ticket_signature[-1] >= 27:
        ticket_signature[-1] -= 27

    # make Signature object to validate data         
    signature = eth_keys.keys.Signature(ticket_signature)
    signerRecoveredPubKey = signature.recover_public_key_from_msg(ticket_body)

    if str(signerRecoveredPubKey) == public_key_in_hex:
        return True
    
    return False


class PluginSettingsView(EventSettingsViewMixin, FormView):
    form_class = forms.PluginSettingsForm
    template_name = 'pretix_attestation_plugin/attestation_plugin_settings.html'
    permission = 'can_change_event_settings'

    def get_context_data(self, **kwargs):
        kwargs["run_sign"] = self.request.build_absolute_uri("?validate_magic_links=1")
        kwargs["validation_result"] = "Unknown"

        if (self.request.GET.get("validate_magic_links")):
            valid_atts = 0
            invalid_atts = 0
            total_atts = 0
            try:
                current_event = self.request.event
                public_key_in_hex = get_public_key_in_hex(event = current_event)

                orders = Order.objects.filter(event = current_event)
                op = OrderPosition.objects.filter(order__in = orders)
                atts = models.AttestationLink.objects.filter(order_position__in = op)

                total_atts = atts.count()
                for a in atts:

                    try:
                        magic_link_params = a.string_url
                        signature_ok = verify_magic_link(public_key_in_hex, magic_link_params=magic_link_params)
                        if signature_ok:
                            valid_atts += 1
                        else:
                            invalid_atts += 1
                    except:
                        invalid_atts += 1
                
                kwargs["validation_result"] = f"Total tickets: {total_atts}, valid: {valid_atts}, invalid: {invalid_atts}"

            except:
                kwargs["validation_result"] = "Can't read private key"

        return super().get_context_data(**kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs["current_base_url"] = models.BaseURL.objects.get(event=self.request.event).string_url
            kwargs["upload"] = models.KeyFile.objects.get(event=self.request.event).upload
        except models.BaseURL.DoesNotExist:
            kwargs["current_base_url"] = "Not set yet"
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
