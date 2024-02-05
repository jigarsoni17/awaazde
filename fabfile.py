import multiprocessing
import sqlite3

from fabric import task
from invoke import run as local

@task
def run_local_backend(context):
    """Starts the local server"""
    local('cd backend && python manage.py runserver 0.0.0.0:8000')


@task
def run_local_frontend(context):
    """Starts the local server for frontend"""
    local('cd frontend && ng serve --port=5555 --watch')


@task
def build_frontend(context):
    """build the frontend for production use"""
    # build with AoT compilation
    local('cd frontend && ng build --prod --aot')


@task
def run_frontend_tests(context):
    """Run the frontend test suits"""
    local('cd frontend && ng test')


@task
def run_tests(context):
    """Run the test suite"""
    local('cd backend && coverage run manage.py test --exclude-tag=public && coverage report -m')
    local('cd backend && coverage run manage.py test --tag=public && coverage report -m')


@task
def setup_local(context):
    setup_local_frontend(context)
    setup_local_backend(context)


@task
def setup_local_frontend(context):
    """Setup frontend dependencies"""
    local('cd frontend && rm -R node_modules')
    local('cd frontend && npm install')


@task
def upgrade_local_frontend(context):
    """Upgrades angular and other dependencies"""
    local('sudo npm uninstall -g angular-cli')
    local('cd frontend && npm uninstall --save-dev angular-cli')
    local('sudo npm cache clean')
    local('sudo npm install -g @angular/cli@1.0.4')
    local('cd frontend && rm -R node_modules')
    local('cd frontend && npm install --save-dev @angular/cli@1.0.4')
    local('cd frontend && npm install')
    local('cd frontend && npm install typescript@2.3.4')
    local('cd frontend && npm install ng2-resource-rest@1.13.0')
    local('cd frontend && npm install webpack-dev-server@2.4.2')


@task
def setup_local_backend(context):
    """Setup local env dependencies"""
    local('pip install -r backend/requirements/local.txt')
    local('python backend/manage.py makemigrations')
    local('python backend/manage.py migrate_schemas')


@task
def setup_public_tenant(context):
    """Setup main tenant for local env"""
    local('python backend/manage.py setup_public_tenant')
    local('python backend/manage.py loaddata dbmail')
    local('python backend/manage.py setup_default_purchase_data')


@task
def setup_test_tenant(context):
    """Setup test tenant for local env"""
    local('python backend/manage.py setup_test_tenant')


def _create_freeswitch_sqlite_cdr_db(cdr_file):
    """
    Create table explicitly since FS doesn't have a configuration hook to modify this table
    (we need to add a few channel variables to the CDR record to match it with Attempts)
    :return: None
    """
    # make file writeable to awaazde by giving group write access
    local('sudo chown freeswitch:awaazde {}'.format(cdr_file))
    local('sudo chmod -R 775 {}'.format(cdr_file))

    connection = sqlite3.connect(cdr_file)
    connection_cursor = connection.cursor()
    connection_cursor.execute(
        'DROP TABLE IF EXISTS "cdr"')
    connection_cursor.execute(
        'CREATE TABLE "cdr" ("caller_id_name" VARCHAR(255) NOT NULL, "caller_id_number" VARCHAR(255) NOT NULL, "destination_number" VARCHAR(255) NOT NULL, "direction" VARCHAR(255) NOT NULL, "context" VARCHAR(255) NOT NULL, "start_stamp" DATETIME NOT NULL, "answer_stamp" DATETIME NOT NULL, "end_stamp" DATETIME NOT NULL, "duration" VARCHAR(255) NOT NULL, "billsec" INTEGER NOT NULL DEFAULT 0, "hangup_cause" VARCHAR(255) NOT NULL, "uuid" VARCHAR(255) NOT NULL, "bleg_uuid" VARCHAR(255) NOT NULL, "account_code" VARCHAR(255) NOT NULL, "schema_name" VARCHAR(255) NOT NULL, "attempt_id" INTEGER NOT NULL DEFAULT 0, "root_flow_node_id" INTEGER NOT NULL DEFAULT 0, "root_flow_node_target_content_type_id" INTEGER NOT NULL DEFAULT 0, "root_flow_node_target_object_id" INTEGER NOT NULL DEFAULT 0)')
    # For FreeSWITCHProvider._get_cdrs_for_attempt_ids() (https://app.asana.com/0/search/1150971026947458/1143866074661908)
    connection_cursor.execute(
        'CREATE INDEX index_on_attempt_id_and_schema_name ON CDR(attempt_id, schema_name)'
    )
    # For CDR.schemas_from_cdrs() (https://chat.awaaz.de/awaazde/pl/6maj1hkjsj8bbqtfmjjkxguono)
    connection_cursor.execute(
        'CREATE INDEX index_on_schema_name ON CDR(schema_name)'
    )
    # For alerts.py (https://app.asana.com/0/850218869668/1150157284923855)
    connection_cursor.execute(
        'CREATE INDEX index_on_start_stamp ON CDR(start_stamp)'
    )

    connection.commit()
    connection.close()

def _freeswitch_channels_to_sessions_per_second(num_channels):
    '''
    A formula to convert number of channels to sessions per second
    Documentation here: https://app.asana.com/0/850218869668/1125459520836592

    UPDATE: Bug 1225 changed this formula

    :param num_channels: Number of channels connected to this system
    :return:
    '''
    # Number of inbound calls at any given second, as a
    # percentage of number of channels
    # This has not been properly calculated but is a rough guess
    INBOUND_CALLS_PERCENTAGE = .1

    # Bug 1225: How much time does it take to send one call over ESL?
    # (https://app.asana.com/0/850218869668/1189199472760154)
    # Choose faster end to be more conservative for sessions setting
    CALL_REQUEST_TIME_SECS = .02

    calls_per_sec_per_thread = float(1/CALL_REQUEST_TIME_SECS)
    # For maximum CPU util bump up the concurrency slightly
    # since EAL is not purely CPU bound (https://app.asana.com/0/850218869668/1189199472760156)
    num_threads = multiprocessing.cpu_count() * 2
    calls_per_sec = int(calls_per_sec_per_thread * num_threads)

    inbound_buffer = float(num_channels * INBOUND_CALLS_PERCENTAGE)
    num_sessions_per_second = int(round(calls_per_sec + inbound_buffer))

    return num_sessions_per_second


@task
def setup_freeswitch_sps(context, num_sps):
    DEFAULT_FS_SESSIONS_PER_SECOND = 30
    if int(num_sps) < DEFAULT_FS_SESSIONS_PER_SECOND:
        print(("Specified sesssions per second ({}) is less than the default ({}). Skipping.".format(num_sps, DEFAULT_FS_SESSIONS_PER_SECOND)))
    local('sudo ./backend/awaazde/ivr/freeswitch/install/freeswitch.sh config-freeswitch-sps {}'.format(num_sps))


@task
def setup_freeswitch_max_sessions(context, num_sessions):
    DEFAULT_FS_MAX_SESSIONS = 1000
    if int(num_sessions) < DEFAULT_FS_MAX_SESSIONS:
        print(("Specified max sesssions ({}) is less than the default ({}). Skipping.".format(num_sessions, DEFAULT_FS_MAX_SESSIONS)))
    local('sudo ./backend/awaazde/ivr/freeswitch/install/freeswitch.sh config-freeswitch-max-sessions {}'.format(num_sessions))


@task
def setup_freeswitch_celery_workers(context, machine_id, num_channels):
    # install supervisor
    # assumes pip is installed since you wouldn't
    # be able to run fab commands without it
    # You should be within virtual env and install supervisor within it
    # For slave servers, since we are only using supervisor for app's celery
    # tasks and other app-specific scripts, it is preferable to install within virtualenv
    print("Installing supervisor")
    # this will only work if you are within your virtual env (i.e. there is no sudo here)
    local('pip install supervisor')

    # setup supervisor process log dirs
    print("Creating log dirs")
    log_root_dir = "$HOME/log"
    local('mkdir -p {}/celery'.format(log_root_dir))
    local('mkdir -p {}/pids'.format(log_root_dir))
    local('mkdir -p {}/lua'.format(log_root_dir))
    # This is required to allow writing of lua log from FS service
    # (corresponds to user/group config in freeswitch.sh:fn_config_freeswitch())
    local('chmod 775 {}/lua'.format(log_root_dir))

    # setup supervisor conf file
    template_conf = './backend/awaazde/ivr/freeswitch/install/freeswitch_conf/supervisor.conf'
    # Read in the file
    with open(template_conf, 'r') as file:
        filedata = file.read()

    # Set number of threads setting in template
    filedata = filedata.replace('{{machine_id}}', str(machine_id))

    # Write conf out to temp location with saved variables
    supervisor_ad_conf_file = '/tmp/awaazde.conf'
    with open(supervisor_ad_conf_file, 'w') as file:
        file.write(filedata)

    print("Installing supervisor conf")
    supervisor_conf_dir = "$HOME/supervisor"
    supervisor_conf_file = "{}/supervisord.conf".format(supervisor_conf_dir)
    supervisor_ad_conf_dir = "conf.d"
    local('mkdir -p {}/{}'.format(supervisor_conf_dir, supervisor_ad_conf_dir))
    local('echo_supervisord_conf > {}'.format(supervisor_conf_file))
    #include dirs are relative paths
    local('echo "[include]\nfiles = {}/*.conf" >> {}'.format(supervisor_ad_conf_dir,
                                                                supervisor_conf_file))
    # copy AD template conf to supervisor conf standard location
    local('cp {} {}/{}'.format(supervisor_ad_conf_file, supervisor_conf_dir, supervisor_ad_conf_dir))

# The default CDR file for FS 10 package-based install
CDR_FILE = "/var/lib/freeswitch/db/cdr.db"


@task
def setup_freeswitch(context, machine_id, num_channels, cdr_file=CDR_FILE):
    _create_freeswitch_sqlite_cdr_db(cdr_file)
    # Set sessions per second in FS configuration
    num_channels = int(num_channels)
    num_sps = _freeswitch_channels_to_sessions_per_second(num_channels)
    setup_freeswitch_sps(context, num_sps)
    setup_freeswitch_max_sessions(context, num_channels)

    # Setup freeswitch-related celery workers
    setup_freeswitch_celery_workers(context, machine_id, num_channels)


@task
def install_setup_freeswitch(context, machine_id, num_channels):
    """Download and install FreeSWITCH on this machine from package"""
    # TODO: any other way to do than explicit sudo? Fabric sudo command doesn't work. Is shell script invocation ok?
    local('sudo ./backend/awaazde/ivr/freeswitch/install/freeswitch.sh install-freeswitch')
    # Do some app-specific, post-installation configuration including updating CDR db and setting params
    setup_freeswitch(context, machine_id, num_channels)

'''
####################################################################################################
IT IS NOT ADVISABLE TO SETUP SANGOMA WITH AD2!

AD2 is fully capable of working with PRI, but Sangoma drivers only support up to FS 1.6, which is only
supported by Debian 8. So we'd be working with old stack.

Also there is an implementation decision made in Messenger scheduler (_get_available_slots)
that will not work well with multiple gateways per single number, which is what PRI setup woud entail

Methods below kept mainly for legacy (AD1) setup purposes
'''
@task
def setup_freeswitch_for_sangoma(context, cdr_file, machine_id, num_channels):
    """Download and install FreeSWITCH on this machine from sources"""
    local('sudo ./backend/awaazde/ivr/freeswitch/install/freeswitch.sh install-freeswitch-for-sangoma')
    setup_freeswitch(context, machine_id, num_channels, cdr_file=cdr_file)


@task
def setup_sangoma(context):
    """Download and install Sangoma driver support for FreeSWITCH on this machine"""
    local('sudo ./backend/awaazde/ivr/freeswitch/install/freeswitch.sh install-sangoma')
'''
####################################################################################################
'''


@task
def run_test_cases(context):
    """Run the test suite"""
    run_allocations_test_cases(context)
    run_billing_test_cases(context)
    run_common_test_cases(context)
    run_contacts_test_cases(context)
    run_content_test_cases(context)
    run_core_test_cases(context)
    run_users_test_cases(context)
    run_dashboard_test_cases(context)
    run_messaging_test_cases(context)
    run_xact_test_cases(context)
    run_adminconsole_test_cases(context)
    ######################
    # run_adminconsole_test_cases(context)
    # run_contacts_test_cases(context)
    # run_content_test_cases(context)
    # run_dashboard_test_cases(context)
    # run_messaging_test_cases(context)
    # run_xact_test_cases(context)


@task
def run_adminconsole_test_cases(context):
    print("==== Running adminconsole test cases=====")
    local('python manage.py test awaazde.web.adminconsole.tests.test_api_views --keepdb')
    local('python manage.py test awaazde.web.adminconsole.tests.test_cart_history --keepdb')
    local('python manage.py test awaazde.web.adminconsole.tests.test_plan_asset_purchase --keepdb')
    local('python manage.py test awaazde.web.adminconsole.tests.test_urls --keepdb')


@task
def run_allocations_test_cases(context):
    print("==== Running allocations test cases=====")
    local('python manage.py test awaazde.web.allocations.tests.test_api_views --keepdb')
    local('python manage.py test awaazde.web.allocations.tests.test_backend_feature_allocation.TestBackendFeaturesAllocationCRUD --keepdb')


@task
def run_billing_test_cases(context):
    print("==== Running billing test cases=====")
    local('python manage.py test awaazde.web.billing.tests.test_api_views --keepdb')
    local('python manage.py test awaazde.web.billing.tests.test_payment_processing --keepdb')


@task
def run_common_test_cases(context):
    print("==== Running common test cases=====")
    local('python manage.py test awaazde.web.common.tests.test_api_views --keepdb')
    local('python manage.py test awaazde.web.common.tests.test_notifications --keepdb')
    local('python manage.py test awaazde.web.common.tests.test_urls --keepdb')


@task
def run_contacts_test_cases(context):
    print("==== Running contacts test cases=====")
    local('python manage.py test awaazde.web.contacts.tests.test_api_views --keepdb')
    local('python manage.py test awaazde.web.contacts.tests.test_custom_field_api_views.TestCustomFilter --keepdb')
    local('python manage.py test awaazde.web.contacts.tests.test_linked_data --keepdb')
    local('python manage.py test awaazde.web.contacts.tests.test_list_api_views --keepdb')
    local('python manage.py test awaazde.web.contacts.tests.test_list_rules --keepdb')
    local('python manage.py test awaazde.web.contacts.tests.test_urls --keepdb')


@task
def run_content_test_cases(context):
    print("==== Running content test cases=====")
    local('python manage.py test awaazde.web.content.tests --keepdb')


@task
def run_core_test_cases(context):
    print("==== Running core test cases=====")
    local('python manage.py test awaazde.web.core.tests.test_auth_views --keepdb')
    local('python manage.py test awaazde.web.core.tests.test_preferences_api --keepdb')
    local('python manage.py test awaazde.web.core.tests.test_urls --keepdb')


@task
def run_dashboard_test_cases(context):
    print("==== Running dashboard test cases=====")
    local('python manage.py test awaazde.web.dashboard.tests.test_reports --keepdb')
    local('python manage.py test awaazde.web.dashboard.tests.test_listener_status_report --keepdb')

@task
def run_messaging_test_cases(context):
    print("==== Running messaging test cases=====")
    # Ideally at this level test cases should pass
    # local('python manage.py test awaazde.web.messaging.tests --keepdb')
    # Next ideal is
   local('python manage.py test awaazde.web.messaging.tests.test_api_views --keepdb')
    
    local('python manage.py test awaazde.web.messaging.tests.test_assets_for_blast --keepdb')
    local('python manage.py test awaazde.web.messaging.tests.test_attempt_updating --keepdb')

    local('python manage.py test awaazde.web.messaging.tests.test_blast_conversion --keepdb')
    
    local('python manage.py test awaazde.web.messaging.tests.test_notifications --keepdb')
    local('python manage.py test awaazde.web.messaging.tests.test_reports --keepdb')
    
    local('python manage.py test awaazde.web.messaging.tests.test_respondent_rules --keepdb')
    local('python manage.py test awaazde.web.messaging.tests.test_scheduling --keepdb')
    
    local('python manage.py test awaazde.web.messaging.tests.test_urls --keepdb')


@task
def run_xact_test_cases(context):
    print("==== Running xact test cases=====")
    # local('python manage.py test awaazde.web.xact.tests --keepdb')
    local('python manage.py test awaazde.web.xact.tests.test_api_views.TestTemplateLanguageAPI --keepdb')
    local('python manage.py test awaazde.web.xact.tests.test_api_views.TestTemplateAPI --keepdb')
    
    local('python manage.py test awaazde.web.xact.tests.test_listener_status_report --keepdb')
    local('python manage.py test awaazde.web.xact.tests.test_message_convert --keepdb')
    
    local('python manage.py test awaazde.web.xact.tests.test_reports --keepdb')
    local('python manage.py test awaazde.web.xact.tests.test_scheduling --keepdb')
    
    local('python manage.py test awaazde.web.xact.tests.test_upload_template.TestFinanceUploadTemplateAPI --keepdb')


@task
def run_users_test_cases(context):
    """Run the test suite"""
    print("==== Running users test cases=====")
    local('python manage.py test awaazde.web.users.tests --keepdb')


@task
def reset_local(context):
    """Reset the db and install with some test data - mainly used in local env"""

    # deleting db and recreating again
    local('psql template1 -c "DROP DATABASE %s"' % ("awaazde"))
    local('psql template1 -c "CREATE DATABASE %s"' % ("awaazde"))
    setup_local_backend(context)
    setup_public_tenant(context)
    setup_test_tenant(context)
    local('python backend/manage.py setup_local_data')
