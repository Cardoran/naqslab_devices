#####################################################################
#                                                                   #
# /naqslab_devices/KeysightXSeries/blacs_tab.py                     #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
from user_devices.naqslab_devices.VISA.blacs_tab import VISATab
from blacs.tab_base_classes import define_state, MODE_MANUAL
from qtutils import UiLoader
import os

class KeysightXScopeTab(VISATab):
    # Event Byte Label Definitions for X series scopes
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
            self.device_worker_class = 'user_devices.naqslab_devices.KeysightXSeries.blacs_worker.KeysightXScopeWorker'
        VISATab.__init__(self,*args,**kwargs)
    
    def initialise_GUI(self):
        # Call the VISATab parent to initialise the STB ui and set the worker
        VISATab.initialise_GUI(self)

        ui = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)),'KeysightXSeries.ui'))
        self.combo_aq_type = ui.combo_aq_type
        self.spin_avg_nr = ui.spinbox_avg_nr
        
        self.combo_aq_type.currentIndexChanged.connect(self.change_aq_type)
        self.spin_avg_nr.valueChanged.connect(self.set_avg_cnt)
        
        self.get_tab_layout().addWidget(ui)
        
        # Set the capabilities of this device
        self.supports_remote_value_check(False)
        self.supports_smart_programming(True) 
        self.statemachine_timeout_add(5000, self.status_monitor)
        
    @define_state(MODE_MANUAL, queue_state_indefinitely=True, delete_stale_states=True)
    def change_aq_type(self,index):
        aqtype = self.combo_aq_type.currentText()
        if aqtype == 'NORMal':
            self.spin_avg_nr.setDisabled(True)
        elif aqtype == 'AVERage':
            self.spin_avg_nr.setDisabled(False)
        yield(self.queue_work(self._primary_worker,'set_aqcuisition_type',aqtype))
        
    @define_state(MODE_MANUAL, queue_state_indefinitely=True, delete_stale_states=True)
    def set_avg_cnt(self,count):
        yield(self.queue_work(self._primary_worker,'set_averaging_number',count))
