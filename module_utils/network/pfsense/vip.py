# -*- coding: utf-8 -*-

# Copyright: (c) 2018, Frederic Bor <frederic.bor@wanadoo.fr>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type
from ansible.module_utils.network.pfsense.module_base import PFSenseModuleBase

VIP_ARGUMENT_SPEC = dict(
    state=dict(default='present', choices=['present', 'absent']),
    interface=dict(required=True, type='str'),
    vhid=dict(type='int'),
    advskew=dict(default=0, type='int'),
    advbase=dict(default=1, type='int'),
    mode=dict(required=True, choices=['ipalias','carp']),
    password=dict(type='str'),
    subnet_bits=dict(default=32, type='int'),
    subnet=dict(required=True, type='str'),
    type=dict(default='single', choices=['single','network']),
    descr=dict(default='', type='str'),
)

VIP_REQUIRED_IF = [
    ["state", "present", ["mode", "interface", "subnet"]],
    ["mode", "carp", ["advskew", "advbase", "password", "vhid"]],
]

class PFSenseVIPModule(PFSenseModuleBase):
    """ module managing pfsense vips """

    @staticmethod
    def get_argument_spec():
        """ return argument spec """
        return VIP_ARGUMENT_SPEC

    ##############################
    # init
    #
    def __init__(self, module, pfsense=None):
        super(PFSenseVIPModule, self).__init__(module, pfsense)
        self.name = "pfsense_vip"
        self.root_elt = self.pfsense.get_element('virtualip')
        self.obj = dict()

        if self.root_elt is None:
            self.root_elt = self.pfsense.new_element('virtualip')
            self.pfsense.root.append(self.root_elt)

        self.setup_vip_cmds = ""

        # get interfaces on which vips can be set
        # function build_if_list https://github.com/pfsense/pfsense/blob/master/src/usr/local/www/firewall_virtual_ip_edit.php
        get_interface_cmd = (
            'require_once("/etc/inc/interfaces.inc");'
            '$list = array();'
            '$interfaces = get_configured_interface_with_descr(true);'
	        '$carplist = get_configured_vip_list("all", VIP_CARP);'

	        'foreach ($carplist as $vipname => $address) {\n'
            '$interfaces[$vipname] = $address;'
		    '$interfaces[$vipname] .= " (";'
		    'if (get_vip_descr($address)) {\n'
			'$interfaces[$vipname] .= get_vip_descr($address);'
		    '} else {\n'
			'$vip = get_configured_vip($vipname);'
			'$interfaces[$vipname] .= "vhid: {$vip["vhid"]}";'
		    '}\n'
		    '$interfaces[$vipname] .= ")";'
	        '}\n'
            '$interfaces["lo0"] = "Localhost";'
            'echo json_encode($interfaces);'
        )

        self.interfaces = self.pfsense.php(get_interface_cmd)

    ##############################
    # params processing
    #
    def _params_to_obj(self):
        """ return a dict from module params """
        params = self.params

        obj = dict()

        obj['interface'] = params['interface']

        if params['mode'] == 'carp':
            obj['vhid'] = str(params['vhid'])
            obj['advskew'] = str(params['advskew'])
            obj['advbase'] = str(params['advbase'])
            obj['password'] = str(params['password'])
        obj['subnet'] = str(params['subnet'])
        obj['subnet_bits'] = str(params['subnet_bits'])
        obj['type'] = str(params['type'])

        obj['descr'] = params['descr']

        obj['mode'] = params['mode']

        return obj

    def _validate_params(self):
        """ do some extra checks on input parameters """
        params = self.params

        # check interface
        if params['interface'] not in self.interfaces.keys():
            if params['interface'].upper() not in self.interfaces.values():
                # check with assign or friendly name
                self.module.fail_json(msg='VIPs can\'t be set on interface {0}. btw, interfaces: {1}'.format(params['interface'], self.interfaces))
            else:
                # if interface is friendly name, get real interface name
                for realname, friendlyname in self.interfaces.items():
                    if params['interface'].upper() == friendlyname:
                        self.params['interface'] = realname
                        break

        # check CARP parameters
        if params['mode'] == 'carp':
            # check vhid
            if params['vhid'] < 1 or params['vhid'] > 255:
                self.module.fail_json(msg='vhid must be between 1 and 255')
            
            # check advskew
            if params['advskew'] < 0 or params['advskew'] > 254:
                self.module.fail_json(msg='advskew must be between 0 and 254')
            
            # check advbase
            if params['advbase'] < 1 or params['advbase'] > 254:
                self.module.fail_json(msg='advbase must be between 1 and 254')

    ##############################
    # XML processing
    #

    def _create_vip_aray(self):
        """ Creates $vip array for creating/removing/editing VIPs """
        vip_array_def = "$vip = array();\n"
        vip_array_def += "$vip['interface'] = '{0}';\n".format(self.obj['interface'])
        vip_array_def += "$vip['mode'] = '{0}';\n".format(self.obj['mode'])
        if self.params['mode'] == 'carp':
            vip_array_def += "$vip['vhid'] = '{0}';\n".format(self.obj['vhid'])
            vip_array_def += "$vip['advskew'] = '{0}';\n".format(self.obj['advskew'])
            vip_array_def += "$vip['advbase'] = '{0}';\n".format(self.obj['advbase'])
            vip_array_def += "$vip['password'] = '{0}';\n".format(self.obj['password'])
        vip_array_def += "$vip['subnet'] = '{0}';\n".format(self.obj['subnet'])
        vip_array_def += "$vip['subnet_bits'] = '{0}';\n".format(self.obj['subnet_bits'])
        vip_array_def += "$vip['descr'] = '{0}';\n".format(self.obj['descr'])
        vip_array_def += "$vip['type'] = '{0}';\n".format(self.obj['type'])

        return vip_array_def

    def _cmd_create(self):
        """ return the php shell to create the virtual IP """
        cmd = self._create_vip_aray()
        cmd += "$vip['uniqid'] = '{0}';\n".format(self.obj['uniqid'])
        if self.params['mode'] == 'ipalias':
            cmd += "interface_ipalias_configure($vip);\n"
        elif self.params['mode'] == 'carp':
            cmd += "$vipif = interface_carp_configure($vip);\n"
            cmd += "if (!get_carp_status()) { set_single_sysctl('net.inet.carp.allow', '1'); }\n"
        return cmd

    def _copy_and_add_target(self):
        """ create the XML target_elt """
        super(PFSenseVIPModule, self)._copy_and_add_target()
        self.setup_vip_cmds += self._cmd_create()

    def _copy_and_update_target(self):
        """ update the XML target_elt """
        before = self.pfsense.element_to_dict(self.target_elt)
        changed = self.pfsense.copy_dict_to_element(self.obj, self.target_elt)
        if self._remove_deleted_params():
            changed = True

        if changed:
            self.obj['uniqid'] = self.target_elt.find('uniqid').text
            self._remove_target_elt()
            self.setup_vip_cmds += self._create_vip_aray()
            self.setup_vip_cmds += "interface_vip_bring_down($vip);"
            self.setup_vip_cmds += self._cmd_create()

        return (before, changed)

    def _create_target(self):
        """ create the XML target_elt """
        self.obj['uniqid'] = self.pfsense.uniqid()
        return self.pfsense.new_element('vip')

    def _find_target(self):
        """ find the XML target_elt """
        return self.pfsense.find_vip(self.obj['interface'], self.obj['mode'], self.obj['descr'], self.obj['subnet'])

    def _pre_remove_target_elt(self):
        """ processing before removing elt """
        cmd = self._create_vip_aray()
        cmd += "interface_vip_bring_down($vip);"
        self.pfsense.phpshell(cmd)

    ##############################
    # run
    #
    def get_update_cmds(self):
        """ build and return php commands to setup virtualip """
        cmd = ''
        if self.setup_vip_cmds != "":
            cmd += self.setup_vip_cmds
        return cmd

    def _update(self):
        """ make the target pfsense reload """
        return self.pfsense.phpshell(self.get_update_cmds())

    ##############################
    # Logging
    #
    def _get_obj_name(self):
        """ return obj's name """
        return "'{0}.{1}.{2}'".format(self.obj['interface'], self.obj['subnet'], self.obj['mode'])

    def _log_fields(self, before=None):
        """ generate pseudo-CLI command fields parameters to create an obj """
        values = ''
        if before is None:
            values += self.format_cli_field(self.obj, 'descr')
            values += self.format_cli_field(self.obj, 'subnet', fname='address')
            values += self.format_cli_field(self.obj, 'mode', fname='mode')
        else:
            values += self.format_updated_cli_field(self.obj, before, 'mode', add_comma=(values), fname='mode')
            values += self.format_updated_cli_field(self.obj, before, 'subnet', add_comma=(values), fname='address')
            values += self.format_updated_cli_field(self.obj, before, 'descr', add_comma=(values))
        return values
