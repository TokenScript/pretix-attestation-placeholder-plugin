all: localecompile
LNGS:=`find pretix_attestation_plugin/locale/ -mindepth 1 -maxdepth 1 -type d -printf "-l %f "`

localecompile:
	django-admin compilemessages

localegen:
	django-admin makemessages --keep-pot -i build -i dist -i "*egg*" $(LNGS)

devserver:
	python -mpretix runserver

devmigrate:
	python -mpretix migrate

.PHONY: all localecompile localegen

dbuild: 
	docker build . -t mypretix --progress=plain

drun: 
	docker run --hostname=e48ba9a54a16 --user=pretixuser --mac-address=02:42:ac:11:00:02 --env=PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin --env=LANG=C.UTF-8 --env=GPG_KEY=E3FF2839C048B25C084DEBE9B26995E310250568 --env=PYTHON_VERSION=3.9.15 --env=PYTHON_PIP_VERSION=22.0.4 --env=PYTHON_SETUPTOOLS_VERSION=58.1.0 --env=PYTHON_GET_PIP_URL=https://github.com/pypa/get-pip/raw/66030fa03382b4914d4c4d0896961a0bdeeeb274/public/get-pip.py --env=PYTHON_GET_PIP_SHA256=1e501cf004eac1b7eb1f97266d28f995ae835d30250bec7f8850562703067dc6 --env=LC_ALL=C.UTF-8 --env=DJANGO_SETTINGS_MODULE=production_settings --volume=/var/pretix-data:/data --volume=/data --volume=/etc/pretix -p 127.0.0.1:8345:80 --restart=no --runtime=runc --rm --name mypretix -d mypretix

drun2: 
	docker run --hostname=pretix_container_hostname \
	 --user=pretixuser \
	 --mac-address=02:42:ac:11:00:02 \
	 --env=PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
	 --env=LANG=C.UTF-8 --env=GPG_KEY=E3FF2839C048B25C084DEBE9B26995E310250568 \
	 --env=PYTHON_VERSION=3.9.15 \
	 --env=PYTHON_PIP_VERSION=22.0.4 \
	 --env=PYTHON_SETUPTOOLS_VERSION=58.1.0 \
	 --env=PYTHON_GET_PIP_URL=https://github.com/pypa/get-pip/raw/66030fa03382b4914d4c4d0896961a0bdeeeb274/public/get-pip.py \
	 --env=PYTHON_GET_PIP_SHA256=1e501cf004eac1b7eb1f97266d28f995ae835d30250bec7f8850562703067dc6 \
	 --env=LC_ALL=C.UTF-8 \
	 --env=DJANGO_SETTINGS_MODULE=production_settings \
	 --volume=/var/pretix-data:/data \
	 --volume=/data \
	 --volume=/etc/pretix \
	 -p 127.0.0.1:8345:80 \
	 --restart=no \
	 --runtime=runc \
	 --rm \
	 --name mypretix \
	 -d \
	 mypretix

drun3:
	docker run --name mypretix -p 127.0.0.1:8345:80 \
    -v /var/pretix-data:/data \
    -v /etc/pretix:/etc/pretix \
    --sysctl net.core.somaxconn=4096 \
	--rm \
	-d \
    mypretix

dstop:
	docker stop mypretix