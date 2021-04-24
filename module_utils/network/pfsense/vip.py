# -*- coding: utf-8 -*-

# Copyright: (c) 2018, Frederic Bor <frederic.bor@wanadoo.fr>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type
from ansible.module_utils.network.pfsense.module_base import PFSenseModuleBase

VIP_ARGUMENT_SPEC = dict(
    state=dict(default='present', choices=['present', 'absent']),
    interface=dict(required=True, type='str'),
    vhid=dict(default=None, type='int'),
    advskew=dict(default=None, type='int'),
    advbase=dict(default=None, type='int'),
    mode=dict(required=True, choices=['ipalias','carp']),
    password=dict(default=None, type='str'),
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
        self.root_elt = self.pfsense.get_element('vips')
        self.obj = dict()

        if self.root_elt is None:
            self.root_elt = self.pfsense.new_element('vips')
            self.pfsense.root.append(self.root_elt)

        self.setup_vip_cmds = ""

        # get physical interfaces on which vips can be set
        get_interface_cmd = (
            'require_once("/etc/inc/interfaces.inc");'
            '$portlist = get_interface_list();'
            '$lagglist = get_lagg_interface_list();'
            '$portlist = array_merge($portlist, $lagglist);'
            'foreach ($lagglist as $laggif => $lagg) {'
            "    $laggmembers = explode(',', $lagg['members']);"
            '    foreach ($laggmembers as $lagm)'
            '        if (isset($portlist[$lagm]))'
            '            unset($portlist[$lagm]);'
            '}')

        if self.pfsense.is_at_least_2_5_0():
            get_interface_cmd += (
                '$list = array();'
                'foreach ($portlist as $ifn => $ifinfo) {'
                '  $list[$ifn] = $ifn . " (" . $ifinfo["mac"] . ")";'
                '  $iface = convert_real_interface_to_friendly_interface_name($ifn);'
                '  if (isset($iface) && strlen($iface) > 0)'
                '    $list[$ifn] .= " - $iface";'
                '}'
                'echo json_encode($list);')
        else:
            get_interface_cmd += (
                '$list = array();'
                'foreach ($portlist as $ifn => $ifinfo)'
                '   if (is_jumbo_capable($ifn))'
                '       array_push($list, $ifn);'
                'echo json_encode($list);')

        self.interfaces = self.pfsense.php(get_interface_cmd)

    ##############################
    # params processing
    #
    def _params_to_obj(self):
        """ return a dict from module params """
        params = self.params

        obj = dict()

        if params['interface'] not in self.interfaces:
            obj['interface'] = self.pfsense.get_interface_port_by_display_name(params['interface'])
            if obj['interface'] is None:
                obj['interface'] = self.pfsense.get_interface_port(params['interface'])
        else:
            obj['interface'] = params['interface']

        if params['state'] == 'present':
            if params['mode'] == 'carp':
                obj['vhid'] = str(params['vhid'])
                obj['advskew'] = str(params['advskew'])
                obj['advbase'] = str(params['advbase'])
                obj['password'] = str(params['password'])
            obj['subnet'] = str(params['subnet'])
            obj['subnet_bits'] = str(params['subnet_bits'])
            obj['type'] = str(params['type'])

            obj['descr'] = params['descr']

        return obj

    def _validate_params(self):
        """ do some extra checks on input parameters """
        params = self.params

        # check interface
        if params['interface'] not in self.interfaces:
            # check with assign or friendly name
            interface = self.pfsense.get_interface_port_by_display_name(params['interface'])
            if interface is None:
                interface = self.pfsense.get_interface_port(params['interface'])

            if interface is None or interface not in self.interfaces:
                self.module.fail_json(msg='VIPs can\'t be set on interface {0}'.format(params['interface']))

        # check vhid
        if params['vhid']:
            if params['vhid'] < 1 or params['vhid'] > 255:
                self.module.fail_json(msg='vhid must be between 1 and 255')
        
        # check advskew
        if params['advskew']:
            if params['advskew'] < 0 or params['advskew'] > 254:
                self.module.fail_json(msg='advskew must be between 1 and 254')
        
        # check advbase
        if params['advbase']:
            if params['advbase'] < 1 or params['advbase'] > 254:
                self.module.fail_json(msg='advbase must be between 1 and 254')

    ##############################
    # XML processing
    #
    def _cmd_create(self):
        """ return the php shell to create the virtual IP """
        cmd = "$vip = array();\n"
        cmd += "$vip['interface'] = '{0}';\n".format(self.obj['interface'])
        cmd += "$vip['mode'] = '{0}';\n".format(self.obj['mode'])
        if self.params['mode'] == 'carp':
            cmd += "$vip['vhid'] = '{0}';\n".format(self.obj['vhid'])
            cmd += "$vip['advskew'] = '{0}';\n".format(self.obj['advskew'])
            cmd += "$vip['advbase'] = '{0}';\n".format(self.obj['advbase'])
            cmd += "$vip['password'] = '{0}';\n".format(self.obj['password'])
        cmd += "$vip['subnet'] = '{0}';\n".format(self.obj['subnet'])
        cmd += "$vip['subnet_bits'] = '{0}';\n".format(self.obj['subnet_bits'])
        cmd += "$vip['descr'] = '{0}';\n".format(self.obj['descr'])
        cmd += "$vipif = interface_vips_configure($vip);\n"

        # cmd += "if ($vipif == NULL || $vipif != $vlan['vlanif']) {pfSense_interface_destroy('%s');} else {\n" % (self.obj['vlanif'])

        # # if vlan is assigned to an interface, configuration needs to be applied again
        # interface = self.pfsense.get_interface_by_port('{0}.{1}'.format(self.obj['interface'], self.obj['tag']))
        # if interface is not None:
        #     cmd += "interface_configure('{0}', true);\n".format(interface)

        # cmd += '}\n'

        return cmd

    def _copy_and_add_target(self):
        """ create the XML target_elt """
        super(PFSenseVIPModule, self)._copy_and_add_target()
        self.setup_vip_cmds += self._cmd_create()

    def _copy_and_update_target(self):
        """ update the XML target_elt """
        old_vipif = self.target_elt.find('vipif').text
        (before, changed) = super(PFSenseVIPModule, self)._copy_and_update_target()
        if changed:
            self.setup_vip_cmds += "pfSense_interface_destroy('{0}');\n".format(old_vipif)
            self.setup_vip_cmds += self._cmd_create()

        return (before, changed)

    def _create_target(self):
        """ create the XML target_elt """
        return self.pfsense.new_element('vip')

    def _find_target(self):
        """ find the XML target_elt """
        return self.pfsense.find_vip(self.obj['interface'], self.obj['subnet'])

    def _pre_remove_target_elt(self):
        """ processing before removing elt """
        pass

    ##############################
    # run
    #
    def get_update_cmds(self):
        """ build and return php commands to setup interfaces """
        cmd = 'require_once("filter.inc");\n'
        if self.setup_vip_cmds != "":
            cmd += 'require_once("interfaces.inc");\n'
            cmd += self.setup_vip_cmds
        cmd += "if (filter_configure() == 0) { clear_subsystem_dirty('filter'); }"
        return cmd

    def _update(self):
        """ make the target pfsense reload """
        return self.pfsense.phpshell(self.get_update_cmds())

    ##############################
    # Logging
    #
    def _get_obj_name(self):
        """ return obj's name """
        return "'{0}.{1}'".format(self.obj['interface'], self.obj['tag'])

    def _log_fields(self, before=None):
        """ generate pseudo-CLI command fields parameters to create an obj """
        values = ''
        if before is None:
            values += self.format_cli_field(self.obj, 'descr')
            values += self.format_cli_field(self.obj, 'pcp', fname='priority')
        else:
            values += self.format_updated_cli_field(self.obj, before, 'pcp', add_comma=(values), fname='priority')
            values += self.format_updated_cli_field(self.obj, before, 'descr', add_comma=(values))
        return values
