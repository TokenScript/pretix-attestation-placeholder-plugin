Pretix Attestation Placeholder Plugin
=====================================

This is a plugin for `pretix`_. 

Pretix Ethereum Plugin Developers

Development setup
-----------------

1. Make sure that you have a working `pretix development setup`_.

2. Clone this repository, eg to ``local/pretix-attestation-placeholder-plugin``.

3. Activate the virtual environment you use for pretix development.

4. Execute ``python setup.py develop`` within this directory to register this application with pretix's plugin registry.

5. Execute ``make`` within this directory to compile translations.

6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.


Steps to configure plugin:
-----------------

1. Enable this plugin in Event -> Settings -> Plugins -> Other

2. Upload PEM file with ECDSA private key in Event -> Settings -> Attestation Plugin Settings

3. Set domain, where TOKEN will be saved (TokenNegotiator outlet must be installed there if you are going to use Ticket with BrandConnector Apps) in Event -> Settings -> Attestation Plugin Settings

4. Select "Ask and require input" for "Ask for email addresses per ticket" in Event -> Settings -> General settings -> Customer data

5. Enable "Send an email to attendees" in Event -> Settings -> E-mail settings -> E-mail Content

6. Update Ticket Email content to insert {attestation_link} for order email and {attendee_attestation_link} for Attendee email in Event -> Settings -> E-mail settings -> E-mail Content


License
-------

Copyright 2021 Pretix Ethereum Plugin Developers

Released under the terms of the MIT License


.. _pretix: https://github.com/pretix/pretix
.. _pretix development setup: https://docs.pretix.eu/en/latest/development/setup.html
