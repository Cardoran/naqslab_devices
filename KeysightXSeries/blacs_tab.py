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
from qtutils.qt.QtGui import QIcon
import os
import numpy as np

def parse_SI(si_string):
    split = si_string.split(" ")
    value = int(split[0])
    suffix = "nµms".split(split[1][0])
    exp = -3*len(suffix[1])
    return np.round(value*10**exp,-exp+1)
def NR3(number):
    num = "{:.1E}".format(float(number))
    return num

class KeysightXScopeTab(VISATab):
    ICON_CROSS = ':qtutils/fugue/cross'
    
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
        
        self.mode_list = []

        self.ui = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)),'KeysightXSeries.ui'))
        self.combo_aq_type = self.ui.combo_aq_type
        self.spin_avg_nr = self.ui.spinbox_avg_nr
        
        self.combo_aq_type.currentIndexChanged.connect(self.change_aq_type)
        self.spin_avg_nr.valueChanged.connect(self.set_avg_cnt)
        self.ui.button_add_mode.clicked.connect(lambda: self.add_mode(self.ui.mode_label.text()))
        self.ui.checkBox_Aqcuisition.clicked.connect(self.use_aqc_cb)
        
        self.get_tab_layout().addWidget(self.ui)
        
        # Set the capabilities of this device
        self.supports_remote_value_check(False)
        self.supports_smart_programming(True) 
        self.statemachine_timeout_add(5000, self.status_monitor)
        
    def add_mode(self, label, source = 0, timescale = 0, yzero = 0):
        mode = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)),'mode_widget.ui'))
        mode.select_button.setText(label)
        mode.close_button.setIcon(QIcon(self.ICON_CROSS))
        mode.cb_source.setCurrentIndex(source)
        mode.cb_timescale.setCurrentIndex(timescale)
        mode.dsb_yzero.setValue(yzero)
        mode.index.setValue(len(self.mode_list))
        mode.index.hide()
        mode.close_button.clicked.connect(lambda: self.remove_mode(mode.index.value()))
        mode.select_button.clicked.connect(
                lambda: self.activate_mode(
                        str(mode.cb_source.currentText()), 
                        str(mode.cb_timescale.currentText()), 
                        mode.dsb_yzero.value()
                        )
                )
        self.mode_list.append(mode)
        self.ui.mode_layout.addWidget(self.mode_list[-1])
        
    def update_mode_indices(self):
        for i in range(len(self.mode_list)):
            mode = self.mode_list[i]
            if mode.index.value() != i:
                mode.index.setValue(i)
        
    def remove_mode(self, index):
        self.ui.mode_layout.removeWidget(self.mode_list[index])
        self.mode_list[index].setParent(None)
        self.mode_list[index] = None
        self.mode_list.pop(index)
        self.update_mode_indices()
        
    @define_state(MODE_MANUAL, queue_state_indefinitely=True, delete_stale_states=True)
    def activate_mode(self, source, timescale, yzero):
        print(source,timescale,yzero)
        ts = parse_SI(timescale)
        print(ts)
        yz = NR3(yzero*ts)
        rang = NR3(10*ts)
        yield(self.queue_work(self._primary_worker,'set_mode',source,rang,yz))
        
    @define_state(MODE_MANUAL, queue_state_indefinitely=True, delete_stale_states=True)
    def change_aq_type(self,index):
        aqtype = self.combo_aq_type.currentText()
        if aqtype == 'NORMal':
            self.spin_avg_nr.setDisabled(True)
        elif aqtype == 'AVERage':
            self.spin_avg_nr.setDisabled(False)
        yield(self.queue_work(self._primary_worker,'set_aqcuisition_type',aqtype))
        
    @define_state(MODE_MANUAL, queue_state_indefinitely=True, delete_stale_states=True)
    def use_aqc_cb(self):
        #self.ui.checkBox_Aqcuisition.setText("Test!")
        if self.ui.checkBox_Aqcuisition.isChecked():
            yield(self.queue_work(self._primary_worker,'change_aqc_state', True))
        else:
            yield(self.queue_work(self._primary_worker,'change_aqc_state', False))
        
    @define_state(MODE_MANUAL, queue_state_indefinitely=True, delete_stale_states=True)
    def set_avg_cnt(self,count):
        yield(self.queue_work(self._primary_worker,'set_averaging_number',count))

    def get_save_data(self):
        data = {}
        data["acq_mode"] = self.combo_aq_type.currentIndex()
        modes_data = []
        for mode in self.mode_list:
            modes_data.append({})
            modes_data[-1]["label"] = mode.select_button.text()
            modes_data[-1]["source"] = mode.cb_source.currentIndex()
            modes_data[-1]["timescale"] = mode.cb_timescale.currentIndex()
            modes_data[-1]["yzero"] = mode.dsb_yzero.value()
        data["modes"] = modes_data
        return data
    
    def restore_save_data(self, data):
        try:
            self.combo_aq_type.setCurrentIndex(data["acq_mode"])
            for mode in data["modes"]:
                self.add_mode(mode["label"],mode["source"],
                              mode["timescale"],mode["yzero"])
        except:
            pass
        return