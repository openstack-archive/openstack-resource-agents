#!/usr/bin/env python

import ConfigParser
import os
import sys

import eventlet
from keystoneauth1.identity.generic import password as ks_password
from keystoneauth1 import session as ks_session
from openstack import connection
from openstack import exceptions
from openstack import service_description
from oslo_config import cfg
from oslo_log import log
from oslo_utils import timeutils

from masakariclient.sdk.ha.v1 import _proxy

LOG = log.getLogger(__name__)
CONF = cfg.CONF
DOMAIN = "masakari_driver"

script_dir = os.path.dirname(os.path.abspath(__file__))

# NOTE: The config file (masakari_driver.conf) is assumed to exist
# in the same directory as this program file.
CONFIG_FILE = script_dir + "/masakari_driver.conf"

default_config = {
    'log_file': None,
    'auth_url': None,
    'project_name': None,
    'project_domain_id': None,
    'username': None,
    'user_domain_id': None,
    'password': None,
    'api_retry_max': 12,
    'api_retry_interval': 10,
}

TYPE_COMPUTE_HOST = "COMPUTE_HOST"
EVENT_STOPPED = "STOPPED"
CLUSTER_STATUS_OFFLINE = "OFFLINE"
HOST_STATUS_NORMAL = "NORMAL"


class MasakariDriver(object):
    def __init__(self, failure_host):
        self.failure_host = failure_host
        self._read_config()
        self._setup_log()

    def _read_config(self):
        """Read configuration file by using ConfigParser."""

        # NOTE: At first I attempted to use oslo.config, but it required
        # either '[--config-dir DIR]' or '[--config-file PATH]' for argument,
        # and the hostname couldn't be passed as an argument.
        # So I use ConfigParser.
        inifile = ConfigParser.SafeConfigParser(default_config)
        inifile.read(CONFIG_FILE)

        self.log_file = inifile.get('DEFAULT', 'log_file')
        self.auth_url = inifile.get('api', 'auth_url')
        self.project_name = inifile.get('api', 'project_name')
        self.project_domain_id = inifile.get('api', 'project_domain_id')
        self.username = inifile.get('api', 'username')
        self.user_domain_id = inifile.get('api', 'user_domain_id')
        self.password = inifile.get('api', 'password')
        self.api_retry_max = int(inifile.get('api', 'api_retry_max'))
        self.api_retry_interval = int(inifile.get('api', 'api_retry_interval'))

    def _setup_log(self):
        """Setup log"""
        if self.log_file is not None:
            CONF.log_file = self.log_file

        log.register_options(CONF)
        log.setup(CONF, DOMAIN)

    def _make_client(self):
        """Make client for a notification."""

        # NOTE: This function uses masakari-monitors's code as reference.

        auth = ks_password.Password(
            auth_url=self.auth_url,
            username=self.username,
            password=self.password,
            user_domain_id=self.user_domain_id,
            project_name=self.project_name,
            project_domain_id=self.project_domain_id)
        session = ks_session.Session(auth=auth)

        desc = service_description.ServiceDescription(
            service_type='ha', proxy_class=_proxy.Proxy)
        conn = connection.Connection(
            session=session, extra_services=[desc])
        conn.add_service(desc)

        client = conn.ha.proxy_class(
            session=session, service_type='ha')

        return client

    def send_notification(self):
        """Send a notification."""

        # NOTE: This function uses masakari-monitors's code as reference.

        # Make event.
        current_time = timeutils.utcnow()
        event = {
            'notification': {
                'type': TYPE_COMPUTE_HOST,
                # Set hostname which was passed as argument.
                'hostname': self.failure_host,
                'generated_time': current_time,
                'payload': {
                    'event': EVENT_STOPPED,
                    'cluster_status': CLUSTER_STATUS_OFFLINE,
                    'host_status': HOST_STATUS_NORMAL
                }
            }
        }
        LOG.info("Send a notification. %s", event)

        # Get client.
        client = self._make_client()

        # Send a notification.
        retry_count = 0
        while True:
            try:
                response = client.create_notification(
                    type=event['notification']['type'],
                    hostname=event['notification']['hostname'],
                    generated_time=event['notification']['generated_time'],
                    payload=event['notification']['payload'])

                LOG.info("Response: %s", response)
                break

            except Exception as e:
                if isinstance(e, exceptions.HttpException):
                    # If http_status is 409, skip the retry processing.
                    if e.status_code == 409:
                        msg = ("Stop retrying to send a notification because "
                               "same notification have been already sent.")
                        LOG.info("%s", msg)
                        break

                if retry_count < self.api_retry_max:
                    LOG.warning("Retry sending a notification. (%s)", e)
                    retry_count = retry_count + 1
                    eventlet.greenthread.sleep(self.api_retry_interval)
                else:
                    LOG.exception("Exception caught: %s", e)
                    break


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: %s <failure hostname>")
        sys.exit(1)

    masakari_driver = MasakariDriver(sys.argv[1])
    masakari_driver.send_notification()

    sys.exit(0)
