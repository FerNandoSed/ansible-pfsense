# Copyright: (c) 2018, Frederic Bor <frederic.bor@wanadoo.fr>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys
import pytest

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
        elt_filter['interface'] = obj['interface']
        elt_filter['subnet'] = obj['subnet']
        elt_filter['mode'] = obj['mode']

        return self.assert_has_xml_tag('virtualip', elt_filter, absent=absent)

    def check_target_elt(self, obj, target_elt):
        """ test the xml definition of virtual IP """

        # checking interface
        self.assert_xml_elt_equal(target_elt, 'interface', obj['interface'])

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

    ##############
    # tests
    #
    def test_vip_create(self):
        """ test creation of a new vip """
        vip = dict(mode='ipalias', subnet='10.240.22.10', descr='', interface='wan', type='single')
        command = "create vip 'wan.10.240.22.10.ipalias', descr='', address='10.240.22.10', mode='ipalias'"
        self.do_module_test(vip, command=command)
