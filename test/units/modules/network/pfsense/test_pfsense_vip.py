# Copyright: (c) 2018, Frederic Bor <frederic.bor@wanadoo.fr>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys
import pytest

from units.compat.mock import patch
from tempfile import mkstemp
from ansible.modules.network.pfsense import pfsense_vip
from ansible.module_utils.network.pfsense.vip import PFSenseVIPModule
from .pfsense_module import TestPFSenseModule

if sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip("pfSense Ansible modules require Python >= 2.7")



class TestPFSenseVIPModule(TestPFSenseModule):
    '''Implements test class for virtual IP module '''

    module = pfsense_vip

    def __init__(self, *args, **kwargs):
        super(TestPFSenseVIPModule, self).__init__(*args, **kwargs)
        self.config_file = 'pfsense_vip_config.xml'
        self.pfmodule = PFSenseVIPModule

    ##############
    # tests utils
    #

    def get_target_elt(self, obj, absent=False):
        """ get the generated vip xml definition """
        elt_filter = {}
        elt_filter['interface'] = self.unalias_interface(obj['interface'])
        elt_filter['subnet'] = obj['subnet']
        elt_filter['mode'] = obj['mode']

        return self.assert_has_xml_tag('virtualip', elt_filter, absent=absent)

    def check_target_elt(self, obj, target_elt):
        """ test the xml definition of virtual IP """

        # checking descr
        if 'descr' in obj:
            self.assert_xml_elt_equal(target_elt, 'descr', obj['descr'])
        else:
            self.assert_xml_elt_is_none_or_empty(target_elt, 'descr')

        # checking subnet
        self.assert_xml_elt_equal(target_elt, 'subnet', obj['subnet'])

        # checking mode
        self.assert_xml_elt_equal(target_elt, 'mode', obj['mode'])

        # check type
        self.assert_xml_elt_equal(target_elt, 'type', obj['type'])

    def setUp(self):
        """ mocking up """
        super(TestPFSenseVIPModule, self).setUp()

        self.mock_parse = patch('ansible.module_utils.network.pfsense.pfsense.ET.parse')
        self.parse = self.mock_parse.start()

        self.mock_shutil_move = patch('ansible.module_utils.network.pfsense.pfsense.shutil.move')
        self.shutil_move = self.mock_shutil_move.start()

        self.mock_php = patch('ansible.module_utils.network.pfsense.pfsense.PFSenseModule.php')
        self.php = self.mock_php.start()
        self.php.return_value = {"wan":"WAN","lan":"LAN","opt1":"VPN","lo0":"Localhost"}

        self.mock_phpshell = patch('ansible.module_utils.network.pfsense.pfsense.PFSenseModule.phpshell')
        self.phpshell = self.mock_phpshell.start()
        self.phpshell.return_value = (0, '', '')

        self.mock_mkstemp = patch('ansible.module_utils.network.pfsense.pfsense.mkstemp')
        self.mkstemp = self.mock_mkstemp.start()
        self.mkstemp.return_value = mkstemp()
        self.tmp_file = self.mkstemp.return_value[1]

        self.mock_chmod = patch('ansible.module_utils.network.pfsense.pfsense.os.chmod')
        self.chmod = self.mock_chmod.start()

        self.mock_get_version = patch('ansible.module_utils.network.pfsense.pfsense.PFSenseModule.get_version')
        self.get_version = self.mock_get_version.start()
        self.get_version.return_value = "2.5.0"

        self.maxDiff = None

    ##############
    # tests
    #
    def test_vip_create_ipalias(self):
        """ test creation of a new vip, ipalias mode """
        vip = dict(mode='ipalias', subnet='10.240.22.10', descr='', interface='wan', type='single')
        command = "create vip 'wan.10.240.22.10.ipalias', descr='', address='10.240.22.10', mode='ipalias'"
        self.do_module_test(vip, command=command)

    def test_vip_create_carp(self):
        """ test creation of a new vip, carp mode """
        vip = dict(mode='carp', subnet='10.240.23.10', descr='', interface='wan', type='single', vhid='200', advskew='0', advbase='1', password='verysecretpassword')
        command = "create vip 'wan.10.240.23.10.carp', descr='', address='10.240.23.10', mode='carp'"
        self.do_module_test(vip, command=command)

    def test_vip_create_ipalias_noop(self):
        """ test creation of a new vip, ipalias mode """
        vip = dict(mode='ipalias', subnet='10.10.20.30', descr='ipaliastest', interface='wan', subnet_bits=27)
        self.do_module_test(vip, changed=False)

    def test_vip_create_carp_noop(self):
        """ test creation of a new vip, carp mode """
        vip = dict(mode='carp', subnet='10.240.22.12', descr='carptest', interface='wan', vhid=240, password='secretpassword')
        self.do_module_test(vip, changed=False)

    def test_vip_create_ipalias_friendly_interface(self):
        """ test creation of a new vip, carp mode """
        vip = dict(mode='ipalias', subnet='10.240.24.10', descr='', interface='vpn', type='single')
        command = "create vip 'opt1.10.240.24.10.ipalias', descr='', address='10.240.24.10', mode='ipalias'"
        self.do_module_test(vip, command=command)

    def test_vip_delete_ipalias_unexistent(self):
        """ test deletion of a vip, ipalias mode """
        vip = dict(mode='ipalias', subnet='10.240.22.10', interface='wan', state='absent')
        command = "delete vip 'wan.10.240.22.10.ipalias'"
        self.do_module_test(vip, command=command, delete=True, changed=False)

    def test_vip_delete_ipalias(self):
        """ test deletion of a vip, ipalias mode """
        vip = dict(mode='ipalias', subnet='10.10.20.30', interface='wan', state='absent')
        command = "delete vip 'wan.10.10.20.30.ipalias'"
        self.do_module_test(vip, command=command, delete=True)

    def test_vip_delete_carp_unexistent(self):
        """ test deletion of a vip, carp mode """
        vip = dict(mode='carp', subnet='10.240.22.10', interface='wan', password='secretpassword', vhid='240', state='absent')
        command = "delete vip 'wan.10.240.22.10.carp'"
        self.do_module_test(vip, command=command, delete=True, changed=False)

    def test_vip_delete_carp(self):
        """ test deletion of a vip, carp mode """
        vip = dict(mode='carp', subnet='10.240.22.12', interface='wan', password='secretpassword', vhid='240', state='absent')
        command = "delete vip 'wan.10.240.22.12.carp'"
        self.do_module_test(vip, command=command, delete=True)

    def test_vip_update_vhid(self):
        """ test update vhid over vip (carp)"""
        vip = dict(mode='carp', subnet='10.240.22.12', interface='wan', password='secretpassword', vhid='24', state='present', type='single', descr='carptest')
        command = "update vip 'wan.10.240.22.12.carp' set vhid='24'"
        self.do_module_test(vip, command=command)

    def test_vip_update_descr_carp(self):
        """ test update vhid over vip (carp)"""
        vip = dict(mode='carp', subnet='10.240.22.12', interface='wan', password='secretpassword', vhid='240', state='present', type='single', descr='')
        command = "update vip 'wan.10.240.22.12.carp' set descr=''"
        self.do_module_test(vip, command=command)

    def test_vip_update_advbase(self):
        """ test update advbase over vip (carp)"""
        vip = dict(mode='carp', subnet='10.240.22.12', interface='wan', password='secretpassword', vhid='240', state='present', type='single', descr='carptest', advbase=10)
        command = "update vip 'wan.10.240.22.12.carp' set advbase='10'"
        self.do_module_test(vip, command=command)

    def test_vip_update_advskew(self):
        """ test update advbase over vip (carp)"""
        vip = dict(mode='carp', subnet='10.240.22.12', interface='wan', password='secretpassword', vhid='240', state='present', type='single', descr='carptest', advskew=100)
        command = "update vip 'wan.10.240.22.12.carp' set advskew='100'"
        self.do_module_test(vip, command=command)

    def test_vip_update_password(self):
        """ test update advbase over vip (carp)"""
        vip = dict(mode='carp', subnet='10.240.22.12', interface='wan', password='verysecretpassword', vhid='240', state='present', type='single', descr='carptest')
        command = "update vip 'wan.10.240.22.12.carp' set password='verysecretpassword'"
        self.do_module_test(vip, command=command)

    def test_vip_update_descr_ipalias(self):
        """ test update descr over vip (ipalis)"""
        vip = dict(mode='ipalias', subnet='10.10.20.30', descr='ipaliastest change', interface='wan', subnet_bits=27, type='single')
        command = "update vip 'wan.10.10.20.30.ipalias' set descr='ipaliastest change'"
        self.do_module_test(vip, command=command)
