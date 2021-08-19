import serial
import serial.tools.list_ports
import tkinter as tk
import threading
import pygubu
import time

class SerialTerminal:
    def __init__(self):

        self.available_baud_rates = [300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 31250, 57600, 115200]

        self.builder = builder = pygubu.Builder()
        builder.add_from_file('serial_terminal.ui')

        self.main_window = builder.get_object('main_window')
        self.serial_menu = builder.get_object('serial_menu')
        self.input = builder.get_object('input')
        self.output = builder.get_object('output')
        self.send_button = builder.get_object('send_button')

        self.baud_rate = tk.IntVar(self.main_window, 9600)
        self.serial_port = tk.StringVar(self.main_window)

        self.serial = serial.Serial()
        self.connected = False

        for speed in self.available_baud_rates:
            self.builder.get_object('baud_rate').add_radiobutton(label=str(speed), var=self.baud_rate, value=speed)

        for port in serial.tools.list_ports.comports():
            self.builder.get_object('serial_port').add_radiobutton(label=port.name, var=self.serial_port, value=port.name)

        self.serial_menu.add_command(label='Connect', command=self.connect_button)

        builder.connect_callbacks(self)

    def write_to_output(self, stri):
        self.output.config(state='normal')
        self.output.insert(tk.END, stri)
        self.output.config(state='disabled')

    def read_serial(self):
        while self.connected:
            if (self.serial.inWaiting() > 0):
                data_str = self.serial.read(self.serial.inWaiting()).decode('ascii')
                self.write_to_output(data_str)
            time.sleep(0.01)

    def write_serial(self):
        self.serial.write(str.encode(self.input.get()))
        self.write_to_output("> " + self.input.get() + "\n")

    def serial_connection_change(self):
        if self.connected:
            self.serial = serial.Serial(self.serial_port.get(), self.baud_rate.get())
            thread = threading.Thread(target=self.read_serial)
            thread.start()
        else:
            self.serial.close()

    def connect_button(self):
        self.connected = not self.connected
        self.serial_menu.entryconfigure(3, label=self.connected and 'Disconnect' or 'Connect')

        self.serial_connection_change()

    def run(self):
        self.main_window.mainloop()


if __name__ == '__main__':
    app = SerialTerminal()
    app.run()
