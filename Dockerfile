FROM pretix/standalone:stable
USER pretixuser
RUN cd /pretix/src && make production

USER root

RUN pip install --upgrade certifi

# RUN cd /home && \ 
# git clone https://github.com/efdevcon/pretix-attestation-placeholder-plugin && \
# cd pretix-attestation-placeholder-plugin && \

COPY . /home
RUN cd /home && \ 
python setup.py install

USER pretixuser
ENTRYPOINT ["pretix"]
CMD ["all"]