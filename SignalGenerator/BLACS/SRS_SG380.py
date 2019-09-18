#####################################################################
#                                                                   #
# /naqslab_devices/SignalGenerator/BLACS/SRS_SG380.py               #
#                                                                   #
# Copyright 2019, Zac Castillo                                      #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2, dedent
if PY2:
    str = unicode

from naqslab_devices.SignalGenerator.blacs_tab import SignalGeneratorTab
from naqslab_devices.SignalGenerator.blacs_worker import SignalGeneratorWorker
from labscript import LabscriptError

class SRS_SG380Tab(SignalGeneratorTab):
    # Capabilities
    base_units = {'freq':'MHz', 'amp':'dBm'}
    base_min = {'freq':0,   'amp':-110} 
    base_max = {'freq':0,  'amp':16.5} # Lower for high frequency models at high freq.
    base_step = {'freq':1,    'amp':1}
    base_decimals = {'freq':9, 'amp':2}
    # Event Status Byte Label Definitions for SRS_SG380 models
    status_byte_labels = {'bit 7':'Power On', 
                          'bit 6':'Reserved',
                          'bit 5':'Command Error',
                          'bit 4':'Execution Error',
                          'bit 3':'Device Error',
                          'bit 2':'Query Error',
                          'bit 1':'Reserved',
                          'bit 0':'Operation Complete'}
    
    def __init__(self,*args,**kwargs):
        self.device_worker_class = SRS_SG380Worker
        SignalGeneratorTab.__init__(self,*args,**kwargs) 
        
class SRS_SG382Tab(SRS_SG380Tab):
    # Capabilities    
     base_max = {'freq':2.025e3,  'amp':16.5} # 2.025 GHz
    
class SRS_SG384Tab(SRS_SG380Tab):
    # Capabilities
    base_max = {'freq':8.100e3,  'amp':16.5} # 8.100 GHz, Must use back panel
    
class SRS_SG386Tab(SRS_SG380Tab):
    # Capabilities
    base_max = {'freq':8.100e3,  'amp':16.5} # 8.100 GHz, Must use back panel

class SRS_SG380Worker(SignalGeneratorWorker):
    # define the scale factor
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6
    amp_scale_factor = 1.0
    
    def init(self):
        '''Calls parent init and sends device specific initialization commands'''        
        SignalGeneratorWorker.init(self)
        try:
            ident_string = self.connection.query('*IDN?')
        except:
            msg = '\'*IDN?\' command did not complete. Is %s connected?'
            if PY2:
                raise LabscriptError(dedent(msg%self.VISA_name))
            else:
                raise LabscriptError(dedent(msg%self.VISA_name)) from None
        
        if 'SG38' not in ident_string:
            msg = '%s is not supported by the SRS_SG380 class.'
            raise LabscriptError(dedent(msg%ident_string))
        
        # enables ESR status reading
        self.connection.write('*ESE 60;*SRE 32;*CLS')
        self.esr_mask = 60
    
    # define instrument specific read and write strings for Freq & Amp control
    # may need to extend to other two outputs
    freq_write_string = 'FREQ {:.6f} HZ' # in Hz	
    freq_query_string = 'FREQ?' #SRS_SG380 returns float, in Hz
    def freq_parser(self,freq_string):
        '''Frequency Query string parser for SRS_SG380
        freq_string format is float, in Hz
        Returns float in instrument units, Hz (i.e. needs scaling to base_units)'''
        return float(freq_string)

    amp_write_string = 'AMPH {:.2f}' # in dBm
    amp_query_string = 'AMPH? ' # in dBm
    def amp_parser(self,amp_string):
        '''Amplitude Query string parser for SRS_SG380
        amp_string format is float in configured units (dBm by default)
        Returns float in instrument units, dBm'''
        return float(amp_string)
        
    def check_status(self):
        # no real info in stb, use esr instead
        esr = int(self.connection.query('*ESR?'))
        
        # if esr is non-zero, read out the error message and report
        # use mask to ignore non-error messages
        if (esr & self.esr_mask) != 0:
            err_list = []
            while True:
                err_code = int(self.connection.query('LERR?'))
                if err_code !=0:
                    err_list.append(err_code)
                else:
                    break
            msg = '{0:s} has errors\n	{1:}'
            raise LabscriptError(dedent(msg.format(self.VISA_name,err_list))) 
        
        return self.convert_register(esr)
