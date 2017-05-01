#!/bin/bash

set -e
set -x

cd ~vagrant/src

# apt-get update

export LC_ALL="en_US.UTF-8"
locale-gen en_US.UTF-8

# Install install Apache bits
apt-get install -y -q libapache2-mod-wsgi

# Install dev things
apt-get install -y -q python-pip python-virtualenv libpython-dev git

# Install postgres
apt-get install -y -q postgresql postgresql-contrib postgresql-server-dev-9.3

# Run postgres at start
update-rc.d postgresql enable
service postgresql start

# Create "vagrant" user and "bc" and "test_bc" databases
sudo -u postgres psql -c "CREATE USER vagrant WITH PASSWORD 'vagrant';"
sudo -u postgres psql -c "ALTER USER vagrant SUPERUSER;"
sudo -u postgres psql -c "CREATE DATABASE bc;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE bc TO vagrant;"
sudo -u postgres psql -c "CREATE DATABASE test_bc;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE test_bc TO vagrant;"

# Install memcached
apt-get install -y -q memcached libmemcached-dev

# Install gettext (used to compile locales)
apt-get install -y -q gettext


# Build virtual environment
VENV=/home/vagrant/env/bc
sudo -H -u vagrant virtualenv $VENV

# Update pip and install BC requirements
sudo -H -u vagrant -s -- <<EOF
source $VENV/bin/activate
pip install --upgrade requests
pip install --upgrade "pip>=8"
cd ~/src
pip install -r requirements/development.txt
EOF

# Remove unused packages, most of them are related to X server
# and we don't use X server at all.
apt-get autoremove -y -q

# Create a .env
cat > /home/vagrant/src/.env <<EOF
DJANGO_DEBUG=1
EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"
SECRET_KEY="seatec astronomy"
DATABASE_URL="postgres://vagrant:vagrant@localhost/bc"
# MEMCACHE_SERVERS='localhost:11211'
# MEMCACHE_USERNAME=''
# MEMCACHE_PASSWORD=''
EOF

# Automatically activate the virtual environment in .bashrc
echo ". $VENV/bin/activate" >> /home/vagrant/.bashrc
