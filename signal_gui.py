from appJar import *
import numpy
import matplotlib.pyplot as plt
import sys
import visa
import math
import time
import numpy as np
import statsmodels.api as sm

class main_gui:
    def __init__(self):
        # Set GUI window
        self.app = gui("RC Filter")
        self.filename = 'wavdata.txt'

        self.unit = {'uHz': 10 ** -6, 'mHz': 10 ** -3, 'Hz': 1, 'kHz': 10 ** 3, 'MHz': 10 ** 6}

        self.type = {"HIGH": 1, "LOW": -1 }


        self.app.startLabelFrame("Sine Wave Generator(CH1)")
        self.app.setSticky("w")
        self.app.setFont(20)
        self.app.addOptionBox("filtertype", ["- Circuit Type -", "HIGH", "LOW"], row=0, column=0)

        self.app.addEntry("freqstart", row=1, column=0)
        self.app.setEntryDefault("freqstart", "Frequency Start")
        self.app.addOptionBox("unitstart", ["- Frequency Unit-", "uHz", "mHz", "Hz", "kHz", "MHz"], row=1, column=1)

        self.app.addEntry("order", row=0, column=1)
        self.app.setEntryDefault("order", "n Order Circuit(interger)")

        self.app.addEntry("freq", row=2, column=0)
        self.app.setEntryDefault("freq", "Frequency Stop")
        self.app.addOptionBox("unit", ["- Frequency Unit-", "uHz", "mHz", "Hz", "kHz", "MHz"], row=2, column=1)

        self.app.addEntry("amplitude", row=3, column=0)
        self.app.setEntryDefault("amplitude", "Amplitude(Vp-p)")

        self.app.addEntry("offset", row=4, column=0)
        self.app.setEntryDefault("offset", "Offset(Vdc)")

        self.app.addEntry("loopnum", row=5, column=0)
        self.app.setEntryDefault("loopnum", "Numbers of Frequency")

        self.app.addEntry("Filename", row=6, column=0)
        self.app.setEntryDefault("Filename", "File Name")

        self.app.addButtons(["Submit", 'Plot'], [self.submit, self.plot])
        self.app.stopLabelFrame()

        # Connect Oscilloscope and Function Generator
        rm = visa.ResourceManager()
        instruments = rm.list_resources()  # Get the list of device id
        usb_instru = list(filter(lambda x: 'USB' in x, instruments))  # Filter and list usb device

        assert len(usb_instru) == 2, 'Require connection from Rigol Oscilloscope and Function wave Generator'

        self.gen = rm.open_resource(usb_instru[0], timeout=5000, chunk_size=1024000)
        self.scope = rm.open_resource(usb_instru[1], timeout=5000, chunk_size=1024000)


    def run(self):
        self.app.go() # Start GUI window


    def genfreq(self):
        # Get all user input
        getOption = self.app.getAllOptionBoxes()
        getEntry = self.app.getAllEntries()

        # Set Oscilloscope and Function generator environment for the circuit
        self.gen.write('OUTP ON')
        time.sleep(0.1)

        self.gen.write('FUNC SIN')
        time.sleep(0.1)

        self.gen.write('VOLT {}'.format(float(getEntry['amplitude'])))
        time.sleep(0.1)

        self.gen.write('VOLT:OFFS {}'.format(float(getEntry['offset'])))
        time.sleep(0.1)

        self.scope.write('CHAN1:DISP ON')
        time.sleep(0.1)

        self.scope.write('CHAN2:DISP ON')
        time.sleep(0.1)

        self.scope.write('CHAN1:COUP DC')
        time.sleep(0.1)

        self.scope.write('CHAN2:COUP DC')
        time.sleep(0.1)

        self.scope.write('CHAN1:OFFS 0')
        time.sleep(0.1)

        self.scope.write('CHAN2:OFFS 0')
        time.sleep(0.1)

        self.scope.write('CHAN1:INV OFF')
        time.sleep(0.1)

        self.scope.write('CHAN2:INV OFF')
        time.sleep(0.1)

        self.scope.write('CHAN1:PROB 1')
        time.sleep(0.1)

        self.scope.write('CHAN2:PROB 1')
        time.sleep(0.1)


        freq_list = []
        vpp_list = []
        diffphase_list = []

        #Initialise start value of experiment
        start_freq = float(getEntry['freqstart']) * float(self.unit[getOption['unitstart']])
        each_freq = start_freq
        bound_freq = float(getEntry['freq']) * float(self.unit[getOption['unit']])
        scope_div = 4
        loopnum = int(getEntry['loopnum'])
        freq_inc = bound_freq / loopnum

        self.filename = getEntry['Filename'] + '.txt'
        file = open(self.filename, 'w')
        file.write('STARTFREQ={0},STOPFREQ={1},AMPLITUTE={2}\n'.format(start_freq, bound_freq, getEntry['amplitude']))
        file.write("Voltage, Frequency, Delta-Phase\n")

        self.gen.write('FREQ {}'.format(each_freq))
        time.sleep(0.1)

        self.scope.write(':TIM:SCAL {}'.format(1 / (scope_div * each_freq)))
        time.sleep(4)

        self.scope.write(':CHAN1:SCAL 1')
        time.sleep(4)

        self.scope.write(':CHAN2:SCAL 1')
        time.sleep(4)

        # Increse frequency value repeatdly until reach stop frequency
        while (each_freq <= bound_freq):
            self.scope.write(':TIM:SCAL {}'.format(1 / (scope_div * each_freq)))

            time.sleep(0.1)

            self.gen.write('FREQ {}'.format(each_freq))
            time.sleep(0.1)

            vpp = float(self.scope.query(":MEASure:VPP? CHAN2"))
            time.sleep(0.1)
            vpp_list.append(vpp)

            diffphase = float(self.scope.query(":MEASure:RPH? CHAN1,CHAN2"))
            time.sleep(0.1)
            diffphase_list.append(diffphase)

            freq_list.append(each_freq)

            file.write("{},{},{}\n".format(vpp, each_freq, diffphase))
            each_freq += freq_inc

        file.close()
        print("vpp: {}".format(vpp_list))
        print("freq: {}".format(freq_list))
        print("phase: {}".format(diffphase_list))


    def plot(self, btn=None):
        getEntry = self.app.getAllEntries()
        getOption = self.app.getAllOptionBoxes()

        circuit_type = self.type[getOption['filtertype']]
        self.filename = getEntry['Filename'] + '.txt'
        file = open(self.filename, 'r')
        data = file.readlines()
        vout = []
        freq = []
        phase = []
        vin = float(data[0].split(',')[2].split('=')[1])
        n_order_multiplier = 20 * int(getEntry['order'])  # Slope of n order circuit

        # Split data in a file to appropriate list for plot
        for each_data in data[2:]:
            data_list = each_data.split(',')
            vout.append(data_list[0])
            freq.append(data_list[1])
            phase.append(data_list[2].strip())

        # Cast all data list to numpy array
        vout = np.array(vout).astype(float)
        freq = np.array(freq).astype(float)
        phase = np.array(phase).astype(float) * circuit_type

        gain = n_order_multiplier * (np.log10(vout / vin)) # Caculate gain of the RC circuit

        # Calculate regression line for smoothed line to represent the data
        least_square_y = np.poly1d(np.polyfit(freq, gain, 15))
        sample_x = np.linspace(freq[0], freq[-1], 500)
        y_predict = least_square_y(sample_x)

        least_square_y_phase = np.poly1d(np.polyfit(freq, phase, 15))
        y_predict_phase = least_square_y_phase(sample_x)

        # Plot graph
        plt.figure(1)

        plt.subplot(211)
        plt.scatter(freq, gain, color='red', label= 'Observe Gain')
        plt.plot(sample_x, y_predict, color='blue', label= 'Gain Prediction')
        plt.title('Frequency Response')
        plt.xscale('log')
        plt.ylabel('Gain = 20log(Vout/Vin)db')
        plt.xlabel('Frequency(Hz)(Logarithmic Scale)')
        plt.legend()
        plt.grid(True)

        plt.subplot(212)
        plt.scatter(freq, phase, color='red', label='Phase Shift Observe')
        plt.plot(sample_x, y_predict_phase, color='blue', label='Phase Shift Prediction')
        plt.title('Phase Shift')
        plt.xscale('linear')
        plt.yscale('linear')
        plt.ylabel('Phase(Degree)')
        plt.xlabel('Frequency(Hz)')
        plt.legend()
        plt.grid(True)

        plt.subplots_adjust(hspace=0.3)

        file.close()
        plt.show()


    def submit(self, btn=None):
        self.genfreq() # Behavior of submit button

    #Switch scope and function generator to appropriate index potision
    def verify_instru(self, usb_instru):
        tmp_var = None

        if 'DG' in usb_instru[0]:
            return usb_instru
        elif 'DG' in usb_instru[1]:
            tmp_var = usb_instru[0]
            usb_instru[0] = usb_instru[1]
            usb_instru[1] = tmp_var

            return usb_instru
        else:
            return None


if __name__ == '__main__':
    window = main_gui()
    window.run()
