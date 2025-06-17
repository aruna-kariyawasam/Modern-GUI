import serial
import serial.tools.list_ports
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class SerialHandler(QObject):
    """Handles all serial communication functionality"""
    data_received = pyqtSignal(int, int)
    connection_status_changed = pyqtSignal(bool, str, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._read_serial_data)
        self.scan_active = False
        
    def get_available_ports(self):
        """Get list of available COM ports"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect_to_port(self, port, baud_rate):
        """Connect to specified COM port"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.disconnect()
                
            self.serial_port = serial.Serial(port, int(baud_rate), timeout=1)
            self.connection_status_changed.emit(True, port, baud_rate)
            return True
            
        except serial.SerialException as e:
            self.serial_port = None
            self.error_occurred.emit(str(e))
            self.connection_status_changed.emit(False, "", "")
            return False
    
    def disconnect(self):
        """Disconnect from current COM port"""
        if self.serial_port and self.serial_port.is_open:
            self.stop_scan()
            self.serial_port.close()
            self.connection_status_changed.emit(False, "", "")
    
    def is_connected(self):
        """Check if serial port is connected"""
        return self.serial_port and self.serial_port.is_open
    
    def start_scan(self):
        """Start scanning for data"""
        if not self.is_connected():
            self.error_occurred.emit("No serial connection available")
            return False
            
        if self.scan_active:
            return True
            
        try:
            self.serial_port.write(b'd#101#1002\n')
            self.scan_active = True
            self.timer.start(100)  # Read every 100ms
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to start scan: {str(e)}")
            return False
    
    def stop_scan(self):
        """Stop scanning for data"""
        if not self.scan_active:
            return
            
        try:
            if self.is_connected():
                self.serial_port.write(b'STOP\n')
            self.timer.stop()
            self.scan_active = False
        except Exception as e:
            self.error_occurred.emit(f"Error stopping scan: {str(e)}")
    
    def _read_serial_data(self):
        """Internal method to read data from serial port"""
        if not self.is_connected() or not self.scan_active:
            self.timer.stop()
            return
        
        try:
            if self.serial_port.in_waiting:
                line = self.serial_port.readline().decode(errors='ignore').strip()
                print("Received:", line)
                
                if line.startswith("d#"):
                    parts = line.split("#")
                    if len(parts) == 3:
                        x = int(parts[1])
                        y = int(parts[2])
                        self.data_received.emit(x, y)
                        
        except Exception as e:
            self.error_occurred.emit(f"Error reading serial data: {str(e)}")
            self.stop_scan()
