# Register your receivers here
from django.dispatch import receiver
from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _
import logging

from pretix.base.signals import (
    register_mail_placeholders,
    order_placed,
    register_ticket_secret_generators
)
from pretix.control.signals import nav_event_settings

from pretix.base.secrets import (
    BaseTicketSecretGenerator,
)

from pretix.base.models import Item, ItemVariation, SubEvent

from .generator.java_generator_wrapper import order_position_attestation_link

import urllib.parse

logger = logging.getLogger(__name__)


@receiver(register_mail_placeholders, dispatch_uid="placeholder_custom")
def register_mail_renderers(sender, **kwargs):
    from .email import OrderAttestationPlaceholder, PositionAttestationPlaceholder
    return [OrderAttestationPlaceholder(), PositionAttestationPlaceholder()]


@receiver(nav_event_settings, dispatch_uid='attestation_nav_key_file_upload')
def navbar_key_file_upload(sender, request, **kwargs):
    url = resolve(request.path_info)
    return [{
        'label': _('Attestation Plugin Settings'),
        'url': reverse('plugins:pretix_attestation_plugin:attestation_plugin_settings', kwargs={
            'event': request.event.slug,
            'organizer': request.organizer.slug,
        }),
        'active': (
            url.namespace == 'plugins:pretix_attestation_plugin'
            and url.url_name == 'attestation_plugin_settings'
        ),
    }]

class RandomTicketSecretGeneratorCustom(BaseTicketSecretGenerator):
    verbose_name =  _('Ticket Attestation')
    identifier = 'ticket_attestation'
    use_revocation_list = False

    def generate_secret(self, item: Item, variation: ItemVariation = None, subevent: SubEvent = None,
                        attendee_name: str = None, current_secret: str = None, force_invalidate=False):
        # placeholder, this secret will be replaced later
        return "_____"

@receiver(register_ticket_secret_generators)
def recv_classic(sender, **kwargs):
    return [RandomTicketSecretGeneratorCustom]

@receiver(order_placed)
def update_ticket_secret(sender, **kwargs):
    order = kwargs['order']
    event = sender

    if event.ticket_secret_generator.identifier == RandomTicketSecretGeneratorCustom.identifier:
        for op in order.positions.all():
            try: 
                attestation_link = order_position_attestation_link(event, op)
                parsed = urllib.parse.urlparse(attestation_link)
                params = urllib.parse.parse_qs(parsed.query)

                ticket_attestation = params['ticket'][0]

                op.secret = ticket_attestation 
                op.save()

            except Exception as e:
                print("Cant update secret. Error: " + str(e))
            
