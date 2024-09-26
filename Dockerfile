### Install pretix
FROM pretix/standalone:stable
# FROM pretix/standalone:4.15.0

USER pretixuser
RUN cd /pretix/src && make production

USER root


# Install Java
RUN apt-get update && apt-get install -y default-jdk

# Set Java PATH
ENV PATH="/usr/lib/jvm/java-8-openjdk-amd64/bin:${PATH}"

COPY . /home
RUN cd /home && python setup.py install

### Run Pretix service
USER pretixuser
ENTRYPOINT ["pretix"]
CMD ["all"]