from pretix.base.email import BaseMailTextPlaceholder
from django.utils.translation import gettext_lazy as _

from .generator.java_generator_wrapper import generate_link, order_position_attestation_link

"""
We need to register two email placeholders under the same name,
the proper one is picked based on the different context.
"""


class OrderAttestationPlaceholder(BaseMailTextPlaceholder):
    def __init__(self):
        self._identifier = "attestation_link"

    @property
    def identifier(self):
        return self._identifier

    @property
    def required_context(self):
        return ['event', 'order']

    def render(self, context):
        order = context['order']
        event = context["event"]

        for position in order.positions.all():
            if position.attendee_email == order.email:
                try:
                    attestation_text = order_position_attestation_link(event, position)
                    print(attestation_text)
                    return attestation_text

                except Exception as e: return(e)   

    def render_sample(self, event):
        return "http://localhost/?ticket=MIGZMAoCAQYCAgTRA…"


class PositionAttestationPlaceholder(BaseMailTextPlaceholder):
    def __init__(self):
        self._identifier = "attendee_attestation_link"

    @property
    def identifier(self):
        return self._identifier

    @property
    def required_context(self):
        return ['event', 'position'] 

    def render(self, context):
        # Change to attestation link        
        position = context["position"]
        event = context["event"]

        try:
            attestation_text = order_position_attestation_link(event, position)
            print("Attestation generated: "+attestation_text)
            return attestation_text
            
        except Exception as e: return(e)   

    def render_sample(self, event):
        return "http://localhost/?ticket=MIGZMAoCAQYCAgTRA…"
