#####################################################################
#                                                                   #
# /naqslab_devices/KeysightXSeries/labscript_device.py              #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
import numpy as np

from user_devices.naqslab_devices import ScopeChannel, CounterScopeChannel
from labscript import Device, TriggerableDevice, config, LabscriptError, set_passed_properties
import h5py

__version__ = '0.1.0'
__author__ = ['dihm']      

class KeysightXScope(TriggerableDevice):
    description = 'Keysight X Series Digital Oscilliscope'
    allowed_children = [ScopeChannel]
    
    @set_passed_properties(property_names = {
        "device_properties":["VISA_name",
                            "compression","compression_opts","shuffle"]}
        )
    def __init__(self, name, VISA_name, trigger_device, trigger_connection, 
        num_AI=4, DI=True,
        compression=None, compression_opts=None, shuffle=False, **kwargs):
        '''VISA_name can be full VISA connection string or NI-MAX alias.
        Trigger Device should be fast clocked device. 
        num_AI sets number of analog input channels, default 4
        DI sets if DI are present, default True
        trigger_duration set scope trigger duration, default 100 us
        Compression of traces in h5 file controlled by:
        compression: \'lzf\', \'gzip\', None 
        compression_opts: 0-9 for gzip
        shuffle: True/False '''
        self.VISA_name = VISA_name
        self.BLACS_connection = VISA_name
        TriggerableDevice.__init__(self,name,trigger_device,trigger_connection,**kwargs)
        
        self.compression = compression
        if (compression == 'gzip') and (compression_opts == None):
            # set default compression level if needed
            self.compression_opts = 4
        else:
            self.compression_opts = compression_opts
        self.shuffle = shuffle
        
        self.allowed_analog_chan = ['Channel {0:d}'.format(i) for i in range(1,num_AI+1)]
        if DI:
            self.allowed_pod1_chan = ['Digital {0:d}'.format(i) for i in range(0,8)]
            self.allowed_pod2_chan = ['Digital {0:d}'.format(i) for i in range(8,16)]
        
        self.measure_settings = {"time_scale":None, "trigger_source":"","x0_position":None}
        
    def generate_code(self, hdf5_file):
        '''Automatically called by compiler to write acquisition instructions
        to h5 file. Configures counters, analog and digital acquisitions.'''    
        Device.generate_code(self, hdf5_file)
        trans = {'pulse':'PUL','edge':'EDG','pos':'P','neg':'N'}
        
        acqs = {'ANALOG':[],'POD1':[],'POD2':[]}
        for channel in self.child_devices:
            if channel.acquisitions:
                # make sure channel is allowed
                if channel.connection in self.allowed_analog_chan:
                    acqs['ANALOG'].append((channel.connection,channel.acquisitions[0]['label']))
                elif channel.connection in self.allowed_pod1_chan:
                    acqs['POD1'].append((channel.connection,channel.acquisitions[0]['label']))
                elif channel.connection in self.allowed_pod2_chan:
                    acqs['POD2'].append((channel.connection,channel.acquisitions[0]['label']))
                else:
                    raise LabscriptError('{0:s} is not a valid channel.'.format(channel.connection))
        
        acquisition_table_dtypes = np.dtype({'names':['connection','label'],'formats':['a256','a256']})
        
        grp = self.init_device_group(hdf5_file)
        # write tables if non-empty to h5_file                        
        for acq_group, acq_chan in acqs.items():
            if len(acq_chan):
                table = np.empty(len(acq_chan),dtype=acquisition_table_dtypes)
                for i, acq in enumerate(acq_chan):
                    table[i] = acq
                grp.create_dataset(acq_group+'_ACQUISITIONS',compression=config.compression,
                                    data=table)
                try:
                    grp[acq_group+'_ACQUISITIONS'].attrs['trigger_time'] = self.trigger_time
                except:
                    raise LabscriptError('device has no trigger given! -> self.trigger_time not defined')
                                    
        # now do the counters
        counts = []
        for channel in self.child_devices:
            if hasattr(channel, 'counts'):
                for counter in channel.counts:
                    counts.append((channel.connection,
                                    trans[counter['type']],
                                    trans[counter['polarity']]))
        counts_table_dtypes = np.dtype({'names':['connection','type','polarity'],'formats':['a256','a256','a256']})
        counts_table = np.empty(len(counts),dtype=counts_table_dtypes)
        for i,count in enumerate(counts):
            counts_table[i] = count
        if len(counts_table):
            grp.create_dataset('COUNTERS',compression=config.compression,data=counts_table)
            grp['COUNTERS'].attrs['trigger_time'] = self.trigger_time
            
        meas_dtypes = [('time_scale',float),('trigger_source',h5py.special_dtype(vlen=str)),('x0_position',float)]
        data = np.array((self.measure_settings["time_scale"],
                         self.measure_settings["trigger_source"],
                         self.measure_settings["x0_position"]),
                         dtype = meas_dtypes)
        grp.create_dataset('MEAS_SETTINGS', data=data)
                                
    def acquire(self,start_time, time_scale=None, trigger_source=None, x0_position=None, trigger_duration=5e-7):
        '''Call to define time when trigger will happen for scope.'''
        if not self.child_devices:
            raise LabscriptError('No channels acquiring for trigger {0:s}'.format(self.name))
        else:
            print(self.parent_device)
            self.parent_device.trigger(start_time,trigger_duration)
            self.trigger_time = start_time
        if time_scale != None:
            self.measure_settings["time_scale"] = time_scale*10
            if x0_position != None:
                self.measure_settings["x0_position"] = x0_position
        elif x0_position != None:
            print("Warning:  y0_position is only used if time_scale is not None!")
        if trigger_source != None:
            self.measure_settings["trigger_source"] = trigger_source