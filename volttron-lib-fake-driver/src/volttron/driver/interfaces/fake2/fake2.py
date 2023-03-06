# -*- coding: utf-8 -*- {{{
# ===----------------------------------------------------------------------===
#
#                 Installable Component of Eclipse VOLTTRON
#
# ===----------------------------------------------------------------------===
#
# Copyright 2022 Battelle Memorial Institute
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# ===----------------------------------------------------------------------===
# }}}

import datetime
import logging
import math
import random
from math import pi

from volttron.driver.base.interfaces import (BaseInterface, BaseRegister, BasicRevert)
from dnp3_python.dnp3station.master_new import MyMasterNew

from typing import List, Type, Dict, Union, Optional, TypeVar

_log = logging.getLogger(__name__)
type_mapping = {
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "bool": bool,
    "boolean": bool
}

# Type alias
RegisterValue = Union[int, str, float, bool]
Register = TypeVar("Register", bound=BaseRegister)


class FakeRegister(BaseRegister):

    def __init__(self, read_only, pointName, units, reg_type, default_value=None, description='',
                 reg_definition=None, master_application=None):
        #     register_type, read_only, pointName, units, description = ''):
        # Note: the most important arguments are regDef and master_application
        # (but keep other arguments by following fake driver example convention)
        self.reg_def = reg_definition
        self.master_application = master_application
        self.reg_type = reg_type
        super(FakeRegister, self).__init__("byte", read_only, pointName, units, description='')


        # if default_value is None:
        #     self.value = self.reg_type(random.uniform(0, 100))
        # else:
        #     try:
        #         self.value = self.reg_type(default_value)
        #     except ValueError:
        #         self.value = self.reg_type()

        self._value = None

    @property
    def value(self):
        master_application = self.master_application
        reg_def = self.reg_def
        group = int(reg_def.get("Group"))
        variation = int(reg_def.get("Variation"))
        index = int(reg_def.get("Index"))
        value = self._get_outstation_pt(master_application, group, variation, index)
        # TODO: add logic that only publish valid value
        return value

    @value.setter
    def value(self, x):
        # TODO: implement this logic
        self._value = x

    @staticmethod
    def _get_outstation_pt(master_application, group, variation, index) -> RegisterValue:
        """
        Core logic to retrieve register value by polling a dnp3 outstation
        Note: using def get_db_by_group_variation_index
        Returns
        -------
        """
        return_point_value = master_application.get_val_by_group_variation_index(group=group,
                                                                                 variation=variation,
                                                                                 index=index)
        return return_point_value


# class EKGregister(BaseRegister):
#
#     def __init__(self, read_only, pointName, units, reg_type, default_value=None, description=''):
#         super(EKGregister, self).__init__("byte", read_only, pointName, units, description='')
#         self._value = 1
#
#         math_functions = ('acos', 'acosh', 'asin', 'asinh', 'atan', 'atan2', 'atanh', 'sin',
#                           'sinh', 'sqrt', 'tan', 'tanh')
#         if default_value in math_functions:
#             self.math_func = getattr(math, default_value)
#         else:
#             _log.error('Invalid default_value in EKGregister.')
#             _log.warning('Defaulting to sin(x)')
#             self.math_func = math.sin
#
#     @property
#     def value(self):
#         now = datetime.datetime.now()
#         seconds_in_radians = pi * float(now.second) / 30.0
#
#         yval = self.math_func(seconds_in_radians)
#
#         return self._value * yval
#
#     @value.setter
#     def value(self, x):
#         self._value = x


class Fake(BasicRevert, BaseInterface):

    def __init__(self, **kwargs):
        super(Fake, self).__init__(**kwargs)
        self.master_application = None  # place-holder: configuration happen in def config(self, ...)

    def configure(self, config_dict, registry_config_str):
        # Note: this method is wired to def get_interface in volttron.driver.base.driver,
        # used `interface.configure(driver_config, registry_config)`
        # Consider this as post_init since config_dict, registry_config_str are not accessible in __init__
        if self.master_application is None:
            driver_config = config_dict
            self.master_application = MyMasterNew(
                masterstation_ip_str=driver_config.get("master_ip"),
                outstation_ip_str=driver_config.get("outstation_ip"),
                port=driver_config.get("port"),
                masterstation_id_int=driver_config.get("master_id"),
                outstation_id_int=driver_config.get("outstation_id"),
            )
            self.master_application.start()  # TODO: complete the self.master_application.stop() logic
        self.parse_config(registry_config_str)

    def get_point(self, point_name):
        register = self.get_register_by_name(point_name)

        # return register.value  # TODO: revert this back
        return "somehting for testing"  # TODO: delete this

    def _set_point(self, point_name, value):
        register = self.get_register_by_name(point_name)
        if register.read_only:
            raise RuntimeError("Trying to write to a point configured read only: " + point_name)

        register.value = register.reg_type(value)
        return register.value

    def _scrape_all(self):
        result = {}
        read_registers = self.get_registers_by_type("byte", True)
        write_registers = self.get_registers_by_type("byte", False)
        for register in read_registers + write_registers:
            result[register.point_name] = register.value

        return result

    def parse_config(self, configDict):
        if configDict is None:
            return

        for regDef in configDict:
            # Skip lines that have no address yet.
            if not regDef['Point Name']:
                continue

            read_only = regDef['Writable'].lower() != 'true'
            point_name = regDef['Volttron Point Name']
            description = regDef.get('Notes', '')
            units = regDef['Units']
            default_value = regDef.get("Starting Value", 'sin').strip()
            if not default_value:
                default_value = None
            type_name = regDef.get("Type", 'string')
            reg_type = type_mapping.get(type_name, str)

            # register_type = FakeRegister if not point_name.startswith('EKG') else EKGregister
            register_type = FakeRegister

            register = register_type(read_only,
                                     point_name,
                                     units,
                                     reg_type,
                                     default_value=default_value,
                                     description=description,
                                     reg_definition=regDef,
                                     master_application=self.master_application)

            if default_value is not None:
                self.set_default(point_name, register.value)

            self.insert_register(register)