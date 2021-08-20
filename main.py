import serial
import serial.tools.list_ports
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.simpledialog import askinteger,askstring
import threading
import pygubu
import configparser
import time
import sys
import os

# Set up configparser and read settings (if it exists)

config = configparser.ConfigParser()
config.read('settings.ini')
config.sections()

settings = {'theme': 'clam'}

for setting in settings.keys():
    if config.has_option('DEFAULT', setting):
        settings[setting] = config['DEFAULT'][setting]
    else:
        config['DEFAULT'][setting] = settings[setting]

# Declare serial terminal class

class SerialTerminal:
    def __init__(self):

        # list of common baud rates
        self.available_baud_rates = [300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 31250, 57600, 115200]

        # generate ui using pygubu
        builder = pygubu.Builder()
        builder.add_from_file('serial_terminal.ui')

        # get required ui elements
        self.main_window = builder.get_object('main_window')
        self.menu_bar = builder.get_object('menu_bar')
        self.file_menu = builder.get_object('file_menu')
        self.serial_menu = builder.get_object('serial_menu')
        self.window_menu = builder.get_object('window_menu')
        self.baud_rate_menu = builder.get_object('baud_rate')
        self.input = builder.get_object('input')
        self.output = builder.get_object('output')
        self.scroll_bar = builder.get_object('output_scroll')
        self.send_button = builder.get_object('send_button')
        self.serial_port_list = builder.get_object('serial_port')

        # set up ui theme
        self.style = ttk.Style(self.main_window)
        self.style.theme_use(settings['theme'])

        # build required variables
        self.baud_rate = tk.IntVar(self.main_window, 9600)
        self.serial_port = tk.StringVar(self.main_window)
        self.clear_output_on_send = tk.BooleanVar(self.main_window, True)
        self.autoscroll = tk.BooleanVar(self.main_window, True)
        self.theme = tk.StringVar(self.main_window, self.style.theme_use())

        # initialize empty serial connection
        self.serial = serial.Serial()
        self.connected = False

        # build runtime ui elements
        self.file_menu.add_command(label='Save output to file...', command=self.save_to_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label='Quit', command=self.shutdown)

        self.window_menu.add_checkbutton(label='Clear Input on Send', var=self.clear_output_on_send)
        self.window_menu.add_checkbutton(label='Autoscroll', var=self.autoscroll)
        self.window_menu.add_separator()
        self.window_menu.add_command(label='Clear Output', command=self.clear_output_text)

        self.baud_rate_menu.add_command(label='Custom', command=self.ask_custom_baud_rate)
        self.baud_rate_menu.add_separator()
        for speed in self.available_baud_rates:
            self.baud_rate_menu.add_radiobutton(label=str(speed), var=self.baud_rate, value=speed)
            
        self.update_port_list()

        for theme_name in self.style.theme_names():
            builder.get_object('theme_menu').add_radiobutton(label=theme_name, var=self.theme, value=theme_name, command=self.change_theme)

        self.serial_menu.add_command(label='Connect', command=self.connect_button)

        # hook callbacks defined using pygubu to class functions
        builder.connect_callbacks(self)

        # link text box and scrollbar
        self.output['yscrollcommand'] = self.scroll_bar.set
        self.scroll_bar.command = self.output.yview

        # set window icon and hook close button to shutdown function
        self.main_window.iconphoto(True, tk.PhotoImage(file='resources/window-icon.png'))
        self.main_window.protocol("WM_DELETE_WINDOW", self.shutdown)

    # displays a prompt to input a custom baud rate
    def ask_custom_baud_rate(self):
        prompt = askinteger('Custom', 'Input a custom baud rate:')
        if prompt:
            self.baud_rate.set(prompt)

    # updates list of available ports in the Serial menu
    def update_port_list(self):
        self.serial_port_list.delete(0, tk.END)
        self.serial_port_list.add_command(label='Refresh', command=self.update_port_list)
        self.serial_port_list.add_separator()
        for port in serial.tools.list_ports.comports():
            self.serial_port_list.add_radiobutton(label=port.description, var=self.serial_port, value=port.device)

    # writes text to the output box
    def write_to_output(self, stri):
        self.output.config(state=tk.NORMAL)
        self.output.insert(tk.END, stri)
        self.output.config(state=tk.DISABLED)
        if self.autoscroll.get():
            self.output.see(tk.END)

    # reads data from pySerial (should be run in a thread)
    def read_serial(self):
        while self.connected:
            try:
                if (self.serial.inWaiting() > 0):
                    data_str = self.serial.read(self.serial.inWaiting()).decode('utf8')
                    self.write_to_output(data_str)
            except serial.serialutil.SerialException:
                self.connected = False
                self.serial_connection_change()
                break
            time.sleep(0.01)

    # writes data to the connected serial port
    def write_serial(self):
        if self.connected:
            self.serial.write(str.encode(self.input.get()))
            if len(self.output.get('1.0', tk.END)) > 1:
                self.write_to_output('\n')
            self.write_to_output('> ' + self.input.get() + '\n')
            if self.clear_output_on_send.get():
                self.input.delete(0, tk.END)

    # enables or disables the serial connection
    def serial_connection_change(self):
        if self.connected:
            self.serial = serial.Serial(self.serial_port.get(), self.baud_rate.get())
            thread = threading.Thread(target=self.read_serial)
            thread.start()
        else:
            self.serial.close()
        try:
            self.menu_bar.entryconfigure(3, label=self.connected and 'Connected' or 'Disconnected')
            self.serial_menu.entryconfigure(3, label=self.connected and 'Disconnect' or 'Connect')
            self.send_button['state'] = self.connected and tk.NORMAL or tk.DISABLED
        except RuntimeError: # occurs when terminal is being closed
            pass


    # handles the connect button in the serial menu
    def connect_button(self):
        if len(self.serial_port.get()) > 0:
            self.connected = not self.connected
            self.serial_connection_change()

    # clears all text in the output box
    def clear_output_text(self):
        self.output.config(state=tk.NORMAL)
        self.output.delete('1.0', tk.END)
        self.output.config(state=tk.DISABLED)

    # changes the ui theme and saves it
    def change_theme(self):
        selected_theme = self.theme.get()

        self.style.theme_use(selected_theme)
        settings['theme'] = selected_theme
        self.save_settings()

    def save_to_file(self):
        prompt = askstring('Save to file', 'File name to save to:')
        if prompt and len(prompt) > 0:
            if not os.path.exists('output'):
                os.makedirs('output')
            file = open(f'output/{prompt}.txt',"w+")
            file.write(self.output.get('1.0', tk.END))
            file.close()

    # saves settings to settings.ini
    def save_settings(self):
        for setting in settings.keys():
            config['DEFAULT'][setting] = settings[setting]
        with open('settings.ini', 'w') as conf:
            config.write(conf)

    # executes neccesary tasks before stopping the script
    def shutdown(self):
        self.connected = False
        self.serial.close()
        self.save_settings()
        sys.exit()

    def run(self):
        self.main_window.mainloop()


if __name__ == '__main__':
    app = SerialTerminal()
    app.run()
