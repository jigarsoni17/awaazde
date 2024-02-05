Awaaz.De
========

**Install Python**

Install Python 3.7.x preferably in a virtualenv/conda environment, and activate it.


**Install Database**

You will need to install postgresql v12.7. In case if you are having older version, you should upgrade it.
For linux, this link_ is really helpful.

For MacOSX (El Capitan), install POSTGRES in the following steps:

1. Install EnterpriseDB_ binary
2. Run_ ``$ xcode-select --install`` to setup zlib
3. Symlink psql and pg_ctl commands if  available: $ sudo ln -s /Library/PostgreSQL/12.X/bin/psql /usr/local/bin/psql
4. Locate_ your pg_hba.conf by running ``$ sudo -u postgres psql -c 'SHOW hba_file;'``
5. In pg_hba.conf, modify the methods of all entries from MD5 to trust
6. Update_ symlinks for psycopg2
7. Reload POSTGRES by running ``$ sudo -u postgres pg_ctl reload -D/Library/PostgreSQL/12.X/data``
8. Restart_ POSTGRES by running ``$ sudo -u postgres pg_ctl -D/Library/PostgreSQL/12.X/data restart``
9. When creating users granting privileges on the DB below (step 2 and 3), will also have to create and grant to the MacOSx user that you are logged in as

**Setup Database**

1. Create the database project: ``$ CREATE DATABASE awaazde;``
2. Create user for database: ``$ CREATE ROLE awaazde WITH LOGIN ENCRYPTED PASSWORD 'awaazde' CREATEDB;``
3. Grant privileges to the user to access database: ``$ GRANT ALL PRIVILEGES ON DATABASE awaazde TO awaazde;``
4. Create hstore extension in default template: Run this outside of psql console ``sudo -u postgres psql -d awaazde -c 'create extension hstore;'``

.. _link: https://computingforgeeks.com/install-postgresql-12-on-ubuntu/
.. _EnterpriseDB: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
.. _Run: http://stackoverflow.com/a/33003406/199754
.. _Locate: http://stackoverflow.com/a/26898164/199754
.. _Update: http://stackoverflow.com/a/33015245/199754
.. _Restart: http://stackoverflow.com/a/16128223/199754

|

**Settings and Local environment**

1. Install dependencies related to setup e.g. fabric, this you can do either inside virtual env or at system level ``$ pip install -r requirements/setup.txt``
2. Install/upgrade nodejs (version >4) if you haven't already.
3. Install angular-cli using command: ``sudo npm install -g @angular/cli`` (use angular version 1.0.4)
4. Create new virtual env and activate it.
5. Copy env.example to .env
6. Change various settings value in .env. Refer to various settings value here: settings_
7. Install influxdb version >= 1.1.x, create database 'ad_test'
8. To setup frontend and local dependencies, execute command ``$ fab setup-local``

.. _settings: http://cookiecutter-django.readthedocs.io/en/latest/settings.html

|

**Basic Commands**

Run following command to run migration and setup public tenant and test tenant::

    $ fab setup-public-tenant
    $ fab setup-test-tenant

|

Run following command to start development server::

    $ fab run-local-backend

Run following command to start frontend server::

    $ fab run-local-frontend

Open Browser and go to 'localhost:5555/'

|

**Test coverage**


To run the tests, just run following command::

    $ fab run-tests

To tun the frontend tests, just run following command ::
    $ fab run-frontend-tests


|

**Celery**


This app comes with Celery.

To run a celery worker:

.. code-block:: bash

    cd awaazde
    sudo apt-get install rabbitmq-server
    systemctl enable rabbitmq-server
    systemctl start rabbitmq-server
    Add/Update in .env file - CELERY_BROKER_URL=amqp://
    Add/Update in settings/local.py - CELERY_TASK_ALWAYS_EAGER=False, CELERY_TASK_EAGER_PROPAGATES=False
    celery -A awaazde.web.taskapp worker -l info

Please note: For Celery's import magic to work, it is important *where* the celery commands are run. If you are in the same folder with *manage.py*, you should be right.

|

**Debian**

Setup vanilla Debian Linux for use as AD2 slave. Assumes you've created user awaazde in install process

1. sudo bash
2. apt-get update
3. apt-get install sudo vim openssh-server git build-essential python-pip
4. Change ssh port if desired
5. Give_ awaazde sudo privilieges
6. Set root password
7. pip install fabric # install fabric
8. clone AD2 repo

Notes

Couldn't get git to clone FS repo until I manually required use of IPv4 by modifying /etc/hosts like this_

.. _Give: https://www.digitalocean.com/community/tutorials/how-to-add-delete-and-grant-sudo-privileges-to-users-on-a-debian-vps
.. _this: https://bitbucket.org/site/master/issues/12184/failed-to-connect-to-bitbucketorg-port-443#comment-29305455

**FreeSWITCH**

.. code-block:: bash
    $ fab install-setup-freeswitch:1,30

You will need to set up a Gateway object to actually send calls. If you do, specify the machine id above (1). The number of channels can also be adjusted but for dev environment you probably won't need to. In backend/awaazde/ivr/freeswitch/lua/common, save a copy of settings_template.lua as settings.lua and enter local settings there.

**Sangoma**

Setup Sangoma driver and config FS

1. install Sangoma hardware in box
2. ``$ fab setup-sangoma``

Notes

You may need to modify ``/etc/wanpipe/wancfg_zaptel/wancfg_zaptel.pl``'s FS conf dir to ``/usr/share/freeswitch/conf/vanilla`` to get the fab command to work


**Deployment**


The following details how to deploy this application.

TODO
