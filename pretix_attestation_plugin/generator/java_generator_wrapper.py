from os import path
from subprocess import Popen, PIPE

from pretix.base.models import OrderPosition

from ..models import (
    AttestationLink,
    BaseURL,
    KeyFile,
)

from django.utils.translation import gettext_lazy as _

import asn1
import urllib.parse
from OpenSSL import crypto
import base64
import eth_keys

"""
A key indicates .pem file in RFC 5915 format.

Before using this generator, key needs to be uploaded through form.
`Attestation Plugin Settings` can be used for that.
"""

def get_private_key_path(event):

    try:
        path_to_key = KeyFile.objects.get(event=event).upload.path
    except KeyFile.DoesNotExist:
        raise( _("Could not generate attestation URL - please contact support@devcon.org (error 2)") )

    if not path.isfile(path_to_key):
        raise ValueError(f'Key file not found in {path_to_key}')
    
    return path_to_key


def get_private_key(event):
    path_to_key = get_private_key_path(event=event)

    with open(path_to_key, 'r') as file:
        key_data = file.read()

    return crypto.load_privatekey(crypto.FILETYPE_PEM, key_data)
    

def get_public_key_in_hex(priv_key):

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


def event_base_url(event):
    try:
        return BaseURL.objects.get(event=event).string_url
    except BaseURL.DoesNotExist:
        raise( _("Could not generate attestation URL - please contact support@devcon.org (error 1)") )

def regenerate_att_link(position, path_to_key):
    try:
        link = generate_link(position, path_to_key)
    except ValueError:
        raise( _("Could not generate attestation URL - please contact support@devcon.org (error 3)") )

    AttestationLink.objects.update_or_create(
        order_position=position,
        defaults={"string_url": link},
    )


# attendee_attestation_link
def order_position_attestation_link(position, base_url, path_to_key):
    
    if not AttestationLink.objects.filter(order_position=position).exists():
        regenerate_att_link(position, path_to_key)

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
