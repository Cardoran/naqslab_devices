#####################################################################
#                                                                   #
# /naqslab_devices/KeysightSA/blacs_tab.py                          #
#                                                                   #
# Copyright 2020, David Meyer                                       #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

from naqslab_devices.VISA.blacs_tab import VISATab 

class KeysightSATab(VISATab):
    # Event Byte Label Definitions for X series spectrum analyzers
    # Used bits set by '*ESE' command in setup string of worker class
    status_byte_labels = {'bit 7':'Powered On', 
                          'bit 6':'Button Pressed',
                          'bit 5':'Command Error',
                          'bit 4':'Execution Error',
                          'bit 3':'Device Error',
                          'bit 2':'Query Error',
                          'bit 1':'Unused',
                          'bit 0':'Operation Complete'}
    
    def __init__(self,*args,**kwargs):
        if not hasattr(self,'device_worker_class'):
            self.device_worker_class = 'naqslab_devices.KeysightSA.blacs_worker.KeysightSAWorker'
        VISATab.__init__(self,*args,**kwargs)
    
    def initialise_GUI(self):
        # Call the VISATab parent to initialise the STB ui and set the worker
        VISATab.initialise_GUI(self)

        # Set the capabilities of this device
        self.supports_remote_value_check(False)
        self.supports_smart_programming(True) 
        self.statemachine_timeout_add(5000, self.status_monitor)        
