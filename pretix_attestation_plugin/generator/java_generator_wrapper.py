from os import path
from subprocess import Popen, PIPE

from pretix.base.models import OrderPosition

from ..models import (
    AttestationLink,
    BaseURL,
    KeyFile,
)

from django.utils.translation import gettext_lazy as _

"""
A key indicates .pem file in RFC 5915 format.

Before using this generator, key needs to be uploaded through form.
`Attestation Plugin Settings` can be used for that.
"""

# attendee_attestation_link
def order_position_attestation_link(event, position):
    
    try:
        path_to_key = KeyFile.objects.get(event=event).upload.path
    except KeyFile.DoesNotExist:
        raise( _("Could not generate attestation URL - please contact support@devcon.org (error 2)") )
    
    if not AttestationLink.objects.filter(order_position=position).exists():
        try:
            link = generate_link(position, path_to_key)
        except ValueError:
            raise( _("Could not generate attestation URL - please contact support@devcon.org (error 3)") )

        AttestationLink.objects.update_or_create(
            order_position=position,
            defaults={"string_url": link},
        )

    try:
        base_url = BaseURL.objects.get(event=event).string_url
    except BaseURL.DoesNotExist:
        raise( _("Could not generate attestation URL - please contact support@devcon.org (error 1)") )

    try:
        return "{base_url}{link}".format(
            base_url=base_url,
            link=str(AttestationLink.objects.get(order_position=position).string_url)
        )

    except AttestationLink.DoesNotExist:
        raise( _("Could not generate attestation URL - please contact support@devcon.org (error 4)") )

def generate_link(order_position: OrderPosition,
                  path_to_key: str,
                  generator_jar: str = 'attestation-all.jar',
                  ticket_status: str = '1') -> str:

    if not path.isfile(path_to_key):
        raise ValueError(f'Key file not found in {path_to_key}')

    # either generator_jar is the full path to the java file or it sits next to the python file
    if path.isfile(generator_jar):
        path_to_generator = path.abspath(generator_jar)
    else:
        this_module_path = path.dirname(path.abspath(__file__))
        path_to_generator = path.join(this_module_path, generator_jar)
    if not path.isfile(path_to_generator):
        raise ValueError(f'Generator file not found in {generator_jar}')

    email = order_position.attendee_email
    event_id = order_position.order.event.id
    # the Java code is accepting only BigInt, so we need to convert a string ID to a number
    pseudonymization_id = order_position.pseudonymization_id
    ticket_id = sum(ord(c) << 8 * i for i, c in enumerate(pseudonymization_id))

    process = Popen(['java', '-cp', path_to_generator,
                     'org.devcon.ticket.Issuer',
                     path_to_key, email,
                     str(event_id), str(ticket_id), ticket_status],
                    stdout=PIPE, stderr=PIPE)

    process.wait()

    error_message = process.stderr.read()
    if (error_message != b''):
        raise ValueError(f'Error message recieved: {error_message}')

    output = process.stdout.read().decode('utf-8')

    return output
