#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, Orion Poplawski <orion@nwra.com>
# Copyright: (c) 2018, Frederic Bor <frederic.bor@wanadoo.fr>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = """
---
module: pfsense_vip
version_added: "2.10"
author: Frederic Bor (@f-bor)
short_description: Manage pfSense VIPs
description:
  - Manage pfSense virtual IPs
notes:
options:
  descr:
    description: The description of the virtual IP.
    default: null
    type: str
  interface:
    description: The interface on which to declare the vip. Friendly name (assignments) can be used.
    required: true
    type: str
  mode:
    description: Mode of virtual IP.
    choices: ["ipalias","carp"]
    required: true
    type: str
  state:
    description: State in which to leave the virtual IP.
    choices: [ "present", "absent" ]
    default: present
    type: str
  subnet:
    description: Declares the IP or subnet which the virtual IP will use.
    required: true
    type: str
  subnet_bits:
    description: Declares the network mask of subnet.
    default: 32
    type: int
  type:
    description: Declares if the virtual IP is a subnet range or a single IP.
    choices: ['single','network']
    default: 'single'
    type: str
  advbase:
    description: Interval (seconds) for carp advertising.
    type: int
    default: 1
  advskew:
    description: Interval (nth of a second) for skew in carp advertising.
    type: int
    default: 0
  vhid:
    description: Virtual IP ID for CARP.
    type: int
  password:
    description: Password for CARP virtual IP.
    type: str
"""

EXAMPLES = """
- name: Add CARP virtual IP
  pfsense_vip:
    interface: wan
    mode: carp
    subnet_bits: 24
    subnet: 10.240.241.2
    descr: testcarp
    vhid: 150
    advskew: 0
    advbase: 1
    password: verysecretpassword

- name: Remove 'testcarp' virtual IP
  pfsense_vlan:
    interface: wan
    mode: carp
    subnet_bits: 24
    subnet: 10.240.241.2
    descr: testcarp
"""

RETURN = """
commands:
    description: the set of commands that would be pushed to the remote device (if pfSense had a CLI)
    returned: always
    type: list
    sample: ["create vlan 'mvneta.100', descr='voice', priority='5'", "update vlan 'mvneta.100', set priority='6'", "delete vlan 'mvneta.100'"]
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.pfsense.vip import PFSenseVIPModule, VIP_ARGUMENT_SPEC, VIP_REQUIRED_IF


def main():
    module = AnsibleModule(
        argument_spec=VIP_ARGUMENT_SPEC,
        required_if=VIP_REQUIRED_IF,
        supports_check_mode=True)

    pfmodule = PFSenseVIPModule(module)
    pfmodule.run(module.params)
    pfmodule.commit_changes()


if __name__ == '__main__':
    main()
