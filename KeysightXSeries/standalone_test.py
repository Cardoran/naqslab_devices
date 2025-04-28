#####################################################################
#                                                                   #
# /naqslab_devices/KeysightXSeries/blacs_worker.py                  #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
import numpy as np
from labscript import LabscriptError
import labscript_utils.properties
from labscript_utils import dedent
from blacs.tab_base_classes import Worker

import pyvisa as visa

class KeysightXScopeWorker(Worker):   
    # define instrument specific read and write strings
    # setup_string = '*ESE 61;*SRE 32;*CLS;:WAV:BYT MSBF;UNS ON;POIN:MODE RAW; :ACQuire:TYPE AVERage; :ACQuire:COUNt 17'
    setup_string = '*ESE 0;*SRE 0;*CLS;:ACQuire:TYPE NORMal;:CHANnel1:DISPlay 1;:CHANnel2:DISPlay 1;:CHANnel3:DISPlay 1;:CHANnel4:DISPlay 1;:CHANnel1:PROBe 1;:CHANnel2:PROBe 1;:CHANnel3:PROBe 1;:CHANnel4:PROBe 1'#;:ACQuire:COUNt 20
    # *ESE does not disable bits in ESR, just their reporting to STB
    # need to use our own mask
    esr_mask = 61
    # note that analog & digital channels require different :WAV:FORM commands
    read_analog_parameters_string = ':WAV:SOUR CHAN{0:d}; :WAV:POIN 5000;:WAV:POIN:MODE NORM; :WAV:BYT MSBF;:WAV:FORM WORD; PRE?'
    # read_analog_parameters_string = ':WAV:FORM WORD;SOUR CHAN{0:d};PRE?'
    read_dig_parameters_string = ':WAV:FORM BYTE;SOUR POD{0:d};PRE?'
    read_waveform_string = ':WAV:DATA?'
    read_counter_string = ':MEAS:{0:s}{1:s}? CHAN{2:d}'
    model_ident = ['SO-X','SOX']
    # some devices need the alternative :SING command, checked for in init()
    dig_command = ':DIG'
    
    def analog_waveform_parser(self,raw_waveform_array,y0,dy,yoffset):
        '''Parses the numpy array from the analog waveform query.'''
        return (raw_waveform_array - yoffset)*dy + y0
        
    def digital_pod_parser(self,raw_pod_array):
        '''Unpacks the bits for a pod array
        Columns returned are in bit order [7,6,5,4,3,2,1,0]'''
        return np.unpackbits(raw_pod_array.astype(np.uint8),axis=0).reshape((-1,8),order='C')
        
    def error_parser(self,error_return_string):
        '''Parses the strings returned by :SYST:ERR?
        Returns int_code, err_string'''
        return int(error_return_string.split(',')[0]), error_return_string
    
    def init(self):
        # Call the VISA init to initialise the VISA connection
        """Initializes basic worker and opens VISA connection to device.
        
        Default connection timeout is 2 seconds"""    
        self.VISA_name = "DSO-X2024A"#self.address
        self.resourceMan = visa.ResourceManager()
        try:
            self.connection = self.resourceMan.open_resource(self.VISA_name)
        except visa.VisaIOError:
            msg = '''{:s} not found! Is it connected?'''.format(self.VISA_name)
            raise LabscriptError(dedent(msg)) from None
        
        # Override the timeout for longer scope waits
        self.connection.timeout = 11000
        self.dig_once = False 
        
        #self.connection.write(':ACQuire:TYPE AVERage')
        #test = self.connection.query( ':ACQuire:TYPE?')
        #print(test)
        
        # Query device name to ensure supported scope
        ident_string = self.connection.query('*IDN?')
        print(ident_string)
        if any(sub in ident_string for sub in self.model_ident):
            print("Scope supported!")
            #If scope is a DSO-X 1000 series, need to use alternate digitize_command for some reason
            if 'DSO-XY' in ident_string:
                print('test')
                self.dig_command = ':SING'
        else:
            raise LabscriptError('Device {0:s} with VISA name {0:s} not supported!'.format(ident_string,self.VISA_name))
        
        # initialization stuff
        self.connection.write(self.setup_string)
        # initialize smart cache
        self.smart_cache = {'COUNTERS': None}
        
        # set osci to auto trigger mode, triggering itself if, after holdoff time 
        # (should be smaller than timeout) no trigger or not enough triggers arrived.
        
        self.connection.write("trigger:sweep normal")
        # self.connection.write("trigger:holdoff 40E-9")
        
    def set_aqcuisition_type(self,aqtype:str):
        if aqtype == 'NORMal' or aqtype == 'AVERage':
            self.connection.write(':ACQuire:TYPE {}'.format(aqtype))
        else:
            raise LabscriptError('Aqcuire type {} is not a valid type or not supported by this implementation yet'.format(aqtype))
        
    def set_averaging_number(self,number:int):
        if number > 0:
            self.connection.write(':ACQuire:COUNt {}'.format(number))
        else:
            raise LabscriptError('Please select a number greater than zero as averaging number!')
        
    def set_mode(self, source, timescale, yzero):
        self.connection.write(':trigger:source {}'.format(source))
        self.connection.write(':timebase:range {}'.format(timescale))
        self.connection.write(':timebase:position {}'.format(yzero))
        self.connection.write(':run')
    
    def transition_to_buffered(self):
        '''This configures counters, if any are defined, 
        as well as optional compression options for saved data traces.'''
        
        # Store the initial values in case we have to abort and restore them:
        # Store the final values to for use during transition_to_static:
        # Store some parameters for saving data later
        
        # self.connection.write("trigger:holdoff 1E0")
        
        print("send_trigger")
        # put scope into single mode
        # necessary since :WAV:DATA? clears data and wait for fresh data
        # when in continuous run mode
        # self.connection.write(self.dig_command)
        time.sleep(1)
        self.connection.write(":TRG")
        # if self.dig_once == False:
        #     self.connection.write(self.dig_command)
        #     self.dig_once = True  
            
    def transition_to_manual(self):
        data = {}
        # query = ':WAV:PRE?'.format(1)
        
        # data = self.connection.query_ascii_values(query)
        query = 'WAV:DATA?'
        print(query)
        time.sleep(1)
        data = self.connection.query_binary_values(query,datatype='H', is_big_endian=True, container=np.array)
        
        
        # channel_num = 1#int(connection.decode('UTF-8').split(' ')[-1])
        # # read an analog channel
        # # use larger chunk size for faster large data reads
        # [form,typ,Apts,cnt,Axinc,Axor,Axref,yinc,yor,yref] = self.connection.query_ascii_values(self.read_analog_parameters_string.format(channel_num))
        # print("data aqcuired!")
        
        # # if Apts*2+11 >= 400000:   # Note that +11 accounts for IEEE488.2 waveform header, not true in unicode (ie Python 3+)
        # #     default_chunk = self.connection.chunk_size
        # #     self.connection.chunk_size = int(Apts*2+11)
        # raw_data = self.connection.query_binary_values(self.read_waveform_string,datatype='H', is_big_endian=True, container=np.array)
        # # print(self.connection.query_binary_values(self.read_analog_parameters_string.format(channel_num),datatype='H', is_big_endian=True, container=np.array))
        # # if Apts*2+11 >= 400000:
        # #     self.connection.chunk_size = default_chunk
        
        # # create the time array
        # data['Analog Time'] = np.arange(Axref,Axref+Apts,1,dtype=np.float64)*Axinc + Axor
            
        # # self.connection.write("trigger:holdoff 40E-9")
        
        # data["1"] = self.analog_waveform_parser(raw_data,yor,yinc,yref)
        # print(data["1"])
    
if __name__ == "__main__":
    import time
    osci = KeysightXScopeWorker()
    osci.init()
    print("transition")
    osci.transition_to_buffered()
    print("buffered")
    osci.transition_to_manual()