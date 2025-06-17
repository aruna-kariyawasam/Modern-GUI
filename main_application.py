import sys
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox, QFileDialog
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
import pyqtgraph as pg
from ModernSpectro import Ui_Form
from serial_handler import SerialHandler
from data_processor import DataProcessor


class MainApp(QWidget):
    """Main application class that coordinates GUI, serial communication, and data processing"""
    
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        
        # Initialize components
        self.serial_handler = SerialHandler()
        self.data_processor = DataProcessor()
        
        # Plot related variables
        self.plot_curve = None
        self.zoom_mode = False
        self.original_view = None
        
        # Setup UI and connections
        self.setup_ui()
        self.setup_connections()
        self.setup_plot_widget()
        
        # Initialize connection status
        self.update_connection_status(False)
        self.update_all_metric_labels()
    
    def setup_ui(self):
        """Initialize UI components"""
        self.populate_com_ports()
        self.max_min_wave_lengths()
    
    def setup_connections(self):
        """Setup all signal-slot connections"""
        # UI button connections
        self.ui.connectBtn.clicked.connect(self.toggle_serial_connection)
        self.ui.startScanBtn.clicked.connect(self.start_scan)
        self.ui.stopScanBtn.clicked.connect(self.stop_scan)
        self.ui.exportCSV.clicked.connect(self.export_csv)
        self.ui.refreshBtn.clicked.connect(self.refresh_com_ports)
        self.ui.clearGrpBtn.clicked.connect(self.clear_graph)
        self.ui.exportPNG.clicked.connect(self.export_graph_as_png)
        self.ui.exportSS.clicked.connect(self.export_screenshot)
        self.ui.zoomBtn.clicked.connect(self.toggle_zoom)
        
        # Serial handler connections
        self.serial_handler.data_received.connect(self.on_data_received)
        self.serial_handler.connection_status_changed.connect(self.on_connection_status_changed)
        self.serial_handler.error_occurred.connect(self.on_error_occurred)
        
        # Data processor connections
        self.data_processor.metrics_updated.connect(self.on_metrics_updated)
    
    def setup_plot_widget(self):
        """Configure the plot widget"""
        self.ui.plotWidget.setBackground('#1e1e2f')
        self.ui.plotWidget.showGrid(x=True, y=True, alpha=0.3)
        self.ui.plotWidget.getAxis('left').setPen(pg.mkPen(color='#ffffff'))
        self.ui.plotWidget.getAxis('bottom').setPen(pg.mkPen(color='#ffffff'))
        self.ui.plotWidget.setLabel('left', "Intensity")
        self.ui.plotWidget.setLabel('bottom', "Wavelength (nm)")
    
    def populate_com_ports(self):
        """Populate COM port dropdown with available ports"""
        self.ui.comPort.clear()
        ports = self.serial_handler.get_available_ports()
        for port in ports:
            self.ui.comPort.addItem(port)
        
        # Add other dropdown items
        self.ui.baudRate.addItems(['9600', '115200', '19200', '38400'])
        self.ui.scanMode.addItems(['Continuous', 'Single'])
        self.ui.plotMode.addItems(['Line', 'Scatter'])
    
    def max_min_wave_lengths(self):
        """Setup wavelength range dropdowns"""
        self.ui.minWaveLength.addItems(['400', '450', '500', '550', '600'])
        self.ui.maxWaveLength.addItems(['700', '750', '800', '850', '900', '950', '1000'])
    
    def toggle_serial_connection(self):
        """Toggle serial connection"""
        if self.serial_handler.is_connected():
            self.serial_handler.disconnect()
        else:
            port = self.ui.comPort.currentText()
            baud = self.ui.baudRate.currentText()
            
            if port and baud:
                success = self.serial_handler.connect_to_port(port, baud)
                if success:
                    pass
                    QMessageBox.information(self, "Connected", f"Connected to {port} at {baud} baud.")
    
    def start_scan(self):
        """Start data scanning"""
        if not self.serial_handler.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to a COM port first.")
            return
        
        if not self.plot_curve:
            self.create_plot_curve()
        
        self.serial_handler.start_scan()
    
    def stop_scan(self):
        """Stop data scanning"""
        self.serial_handler.stop_scan()
    
    def create_plot_curve(self):
        """Create a new plot curve with the appropriate style"""
        if self.ui.plotMode.currentText() == "Scatter":
            self.plot_curve = self.ui.plotWidget.plot(
                [], [], 
                pen=None, 
                symbol='o', 
                symbolSize=5, 
                symbolBrush='#1f77b4',
                symbolPen='w'
            )
        else:
            self.plot_curve = self.ui.plotWidget.plot(
                [], [], 
                pen=pg.mkPen(color='#1f77b4', width=2)
            )
    
    def update_plot(self):
        """Update the plot with current data"""
        if not self.plot_curve:
            self.create_plot_curve()
        
        x_vals, y_vals = self.data_processor.get_plot_data()
        if x_vals and y_vals:
            self.plot_curve.setData(x_vals, y_vals)
    
    def clear_graph(self):
        """Clear graph and all data"""
        self.data_processor.clear_data()
        if self.plot_curve:
            self.ui.plotWidget.removeItem(self.plot_curve)
            self.plot_curve = None
        QMessageBox.information(self, "Cleared", "Graph and data have been cleared.")
    
    def export_csv(self):
        """Export data to CSV"""
        self.data_processor.export_to_csv(self)
    
    def export_graph_as_png(self):
        """Export graph as PNG"""
        self.data_processor.export_plot_as_png(self.ui.plotWidget, self)
    
    def export_screenshot(self):
        """Export screenshot of entire application"""
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "", "PNG Files (*.png)", options=options
        )
        
        if filename:
            try:
                pixmap = self.grab()
                pixmap.save(filename, "PNG")
                QMessageBox.information(self, "Screenshot Saved", f"Screenshot saved as {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save screenshot:\n{e}")
    
    def toggle_zoom(self):
        """Toggle zoom mode for the plot"""
        self.zoom_mode = not self.zoom_mode
        
        if self.zoom_mode:
            self.ui.zoomBtn.setText("Reset View")
            self.ui.zoomBtn.setStyleSheet(
                "QPushButton {"
                "    background-color: #1ab394; "
                "    color: black;"
                "    border: 1px solid #3c3c5c;"
                "    border-radius: 15px;"
                "    padding: 6px 12px;"
                "}"
            )
            self.original_view = self.ui.plotWidget.viewRange()
        else:
            self.ui.zoomBtn.setText("Zoom")
            self.ui.zoomBtn.setStyleSheet(
                "QPushButton {"
                "    background-color: #945c5c; "
                "    color: black;"
                "    border: 1px solid #3c3c5c;"
                "    border-radius: 15px;"
                "    padding: 6px 12px;"
                "}"
            )
            if self.original_view:
                self.ui.plotWidget.setRange(xRange=self.original_view[0], yRange=self.original_view[1])
    
    def refresh_com_ports(self):
        """Refresh available COM ports"""
        self.populate_com_ports()
        QMessageBox.information(self, "Refreshed", "COM ports have been refreshed.")
    
    def update_connection_status(self, connected, port=None, baud=None):
        """Update connection status display"""
        if connected and port and baud:
            self.ui.ConStatus.setText(f"Connected {port} @ {baud}")
            self.ui.ConStatus.setStyleSheet(
                "background-color: #07072b; "
                "color: white; "
                "border-radius: 30px; "
                "padding: 2px 10px; "
                "font-weight: bold; "
                "font-size: 16px; "
                "text-align: center; "
                "border: 1px solid #1d990f;"
            )
            
            self.ui.connectBtn.setText("Disconnect")
            self.ui.connectBtn.setStyleSheet(
                "background-color: #f00e0e; "
                "color: black; "
                "border-radius: 15px; "
                "border: 1px solid #cf1111;"
            )
        else:
            self.ui.ConStatus.setText("Disconnected the Board")
            self.ui.ConStatus.setStyleSheet(
                "background-color: #07072b; "
                "color: white; "
                "border-radius: 30px; "
                "padding: 2px 10px; "
                "font-weight: bold; "
                "text-align: center; "
                "font-size: 18px; "
                "border: 1px solid #cf1111;"
            )
            
            self.ui.connectBtn.setText("Connect")
            self.ui.connectBtn.setStyleSheet(
                "QPushButton {"
                    "background-color: #4c8c0b;"
                    "color:black;"
                    "border: 1px solid #3c3c5c;"
                    "border-radius: 15px;"
                    "padding: 6px 12px;"
                "}"
                "QPushButton:hover {"
                    "background-color: #234203;"
                    "color: white;"
                "}"
            )
    
    def update_all_metric_labels(self):
        """Update all metric display labels"""
        metrics_text = self.data_processor.get_metrics_text()
        self.ui.peadValue.setText(metrics_text['peak_value'])
        self.ui.centroid.setText(metrics_text['centroid'])
        self.ui.maxIntensity.setText(metrics_text['max_intensity'])
        self.ui.fwhm.setText(metrics_text['fwhm'])
        self.ui.snr.setText(metrics_text['snr'])
        self.ui.auc.setText(metrics_text['auc'])
    
    # Signal handlers
    def on_data_received(self, x, y):
        """Handle new data received from serial"""
        self.data_processor.add_data_point(x, y)
        self.update_plot()
    
    def on_connection_status_changed(self, connected, port, baud):
        """Handle connection status changes"""
        self.update_connection_status(connected, port, baud)
    
    def on_error_occurred(self, error_message):
        """Handle errors from serial handler"""
        QMessageBox.critical(self, "Error", error_message)
    
    def on_metrics_updated(self, metrics):
        """Handle metrics updates from data processor"""
        self.update_all_metric_labels()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.setWindowTitle("SpectroPro Ultra")
    window.show()
    sys.exit(app.exec_())
