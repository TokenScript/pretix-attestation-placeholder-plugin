### Install pretix
# FROM pretix/standalone:stable
FROM pretix/standalone:4.15.0
USER pretixuser
RUN cd /pretix/src && make production

USER root

### update PIP
# RUN pip install --upgrade certifi

# WORKDIR /home

# ### Install PostgreSQL
# # Create the file repository configuration:
# RUN sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

# # Import the repository signing key:
# RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# # Update the package lists:
# RUN apt-get update

# # Install the latest version of PostgreSQL.
# # If you want a specific version, use 'postgresql-12' or similar instead of 'postgresql':
# RUN apt-get -y install postgresql

RUN pip install pytest

### Install plugin
RUN cd /home && \ 
git clone https://github.com/efdevcon/pretix-attestation-placeholder-plugin && \
cd pretix-attestation-placeholder-plugin && \
python setup.py install

# COPY . /home
# RUN  cd /home && python setup.py install
# RUN python -v /home/tests/link/test_java_link_generator.py

### Run Pretix service
USER pretixuser
ENTRYPOINT ["pretix"]
CMD ["all"]