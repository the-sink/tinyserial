import serial
import serial.tools.list_ports
import tkinter as tk
import tkinter.ttk as ttk
import threading
import pygubu
import time
import sys

# TODO: comments for the love of god

class SerialTerminal:
    def __init__(self):

        self.available_baud_rates = [300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 31250, 57600, 115200]

        builder = pygubu.Builder()
        builder.add_from_file('serial_terminal.ui')

        self.main_window = builder.get_object('main_window')
        self.menu_bar = builder.get_object('menu_bar')
        self.serial_menu = builder.get_object('serial_menu')
        self.window_menu = builder.get_object('window_menu')
        self.input = builder.get_object('input')
        self.output = builder.get_object('output')
        self.scroll_bar = builder.get_object('output_scroll')
        self.send_button = builder.get_object('send_button')

        self.serial_port_list = builder.get_object('serial_port')

        self.style = ttk.Style(self.main_window)
        self.style.theme_use('clam')

        self.baud_rate = tk.IntVar(self.main_window, 9600)
        self.serial_port = tk.StringVar(self.main_window)
        self.clear_output_on_send = tk.BooleanVar(self.main_window, True)
        self.autoscroll = tk.BooleanVar(self.main_window, True)
        self.theme = tk.StringVar(self.main_window, self.style.theme_use())

        self.serial = serial.Serial()
        self.connected = False

        self.window_menu.add_checkbutton(label='Clear Input on Send', var=self.clear_output_on_send)
        self.window_menu.add_checkbutton(label='Autoscroll', var=self.autoscroll)
        self.window_menu.add_separator()
        self.window_menu.add_command(label='Clear Output', command=self.clear_output_text)

        for speed in self.available_baud_rates:
            builder.get_object('baud_rate').add_radiobutton(label=str(speed), var=self.baud_rate, value=speed)
            
        self.update_port_list()

        for theme_name in self.style.theme_names():
            builder.get_object('theme_menu').add_radiobutton(label=theme_name, var=self.theme, value=theme_name, command=self.change_theme)

        self.serial_menu.add_command(label='Connect', command=self.connect_button)

        builder.connect_callbacks(self)

        self.output['yscrollcommand'] = self.scroll_bar.set
        self.scroll_bar.command = self.output.yview

        self.main_window.iconphoto(True, tk.PhotoImage(file='resources/window-icon.png'))
        self.main_window.protocol("WM_DELETE_WINDOW", self.shutdown)

    def update_port_list(self):
        self.serial_port_list.delete(0, tk.END)
        self.serial_port_list.add_command(label='Refresh', command=self.update_port_list)
        self.serial_port_list.add_separator()
        for port in serial.tools.list_ports.comports():
            self.serial_port_list.add_radiobutton(label=port.description, var=self.serial_port, value=port.device)

    def write_to_output(self, stri):
        self.output.config(state=tk.NORMAL)
        self.output.insert(tk.END, stri)
        self.output.config(state=tk.DISABLED)
        if self.autoscroll.get():
            self.output.see(tk.END)

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

    def write_serial(self):
        if self.connected:
            self.serial.write(str.encode(self.input.get()))
            if len(self.output.get('1.0', tk.END)) > 1:
                self.write_to_output('\n')
            self.write_to_output('> ' + self.input.get() + '\n')
            if self.clear_output_on_send.get():
                self.input.delete(0, tk.END)

    def serial_connection_change(self):
        if self.connected:
            self.serial = serial.Serial(self.serial_port.get(), self.baud_rate.get())
            thread = threading.Thread(target=self.read_serial)
            thread.start()
        else:
            self.serial.close()
        try:
            self.menu_bar.entryconfigure(2, label=self.connected and 'Connected' or 'Disconnected')
            self.serial_menu.entryconfigure(3, label=self.connected and 'Disconnect' or 'Connect')
            self.send_button['state'] = self.connected and tk.NORMAL or tk.DISABLED
        except RuntimeError: # occurs when terminal is being closed
            pass


    def connect_button(self):
        if len(self.serial_port.get()) > 0:
            self.connected = not self.connected
            self.serial_connection_change()

    def clear_output_text(self):
        self.output.config(state=tk.NORMAL)
        self.output.delete('1.0', tk.END)
        self.output.config(state=tk.DISABLED)

    def change_theme(self):
        self.style.theme_use(self.theme.get())

    def shutdown(self):
        self.connected = False
        self.serial.close()
        sys.exit()

    def run(self):
        self.main_window.mainloop()


if __name__ == '__main__':
    app = SerialTerminal()
    app.run()
