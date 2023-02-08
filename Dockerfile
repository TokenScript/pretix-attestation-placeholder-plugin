### Install pretix
# FROM pretix/standalone:stable
FROM pretix/standalone:4.15.0
USER pretixuser
RUN cd /pretix/src && make production

USER root

### update PIP
# RUN pip install --upgrade certifi

# WORKDIR /home

# RUN pip install pytest

### Install plugin
# RUN cd /home && \ 
# git clone https://github.com/efdevcon/pretix-attestation-placeholder-plugin && \
# cd pretix-attestation-placeholder-plugin && \
# python setup.py install

COPY . /home
RUN rm /home/tests/link/test_java_link_generator.py
RUN cd /home && python setup.py install
# RUN python -v /home/tests/link/test_java_link_generator.py

### Run Pretix service
USER pretixuser
ENTRYPOINT ["pretix"]
CMD ["all"]