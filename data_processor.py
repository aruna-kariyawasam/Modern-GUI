import numpy as np
import csv
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import pyqtgraph as pg
import pyqtgraph.exporters


class DataProcessor(QObject):
    """Handles data processing, metrics calculation, and export functionality"""
    
    # Signals for communication with main application
    metrics_updated = pyqtSignal(dict)  # Updated metrics dictionary
    
    def __init__(self):
        super().__init__()
        self.data_points = []
        self.metrics = {
            'peak_value': 0,
            'centroid': 0,
            'max_intensity': 0,
            'fwhm': 0,
            'snr': 0,
            'auc': 0
        }
    
    def add_data_point(self, x, y):
        """Add a new data point to the dataset"""
        self.data_points.append((x, y))
        self.calculate_metrics()
        self.metrics_updated.emit(self.metrics.copy())
    
    def clear_data(self):
        """Clear all data points and reset metrics"""
        self.data_points = []
        self.reset_metrics()
        self.metrics_updated.emit(self.metrics.copy())
    
    def get_data_points(self):
        """Get current data points"""
        return self.data_points.copy()
    
    def get_plot_data(self):
        """Get data formatted for plotting"""
        if not self.data_points:
            return [], []
        return zip(*self.data_points)
    
    def calculate_metrics(self):
        """Calculate all metrics based on current data"""
        if not self.data_points:
            self.reset_metrics()
            return
            
        # Extract wavelengths and intensities
        wavelengths, intensities = zip(*self.data_points)
        intensities = np.array(intensities)
        wavelengths = np.array(wavelengths)
        
        # Calculate peak value and max intensity
        max_intensity = np.max(intensities)
        peak_idx = np.argmax(intensities)
        peak_value = wavelengths[peak_idx]
        
        # Calculate centroid
        if np.sum(intensities) > 0:
            centroid = np.sum(wavelengths * intensities) / np.sum(intensities)
        else:
            centroid = 0
        
        # Calculate FWHM
        half_max = max_intensity / 2
        above_half = intensities > half_max
        
        if np.any(above_half):
            left_idx = np.argmax(above_half)
            right_idx = len(above_half) - np.argmax(above_half[::-1]) - 1
            if right_idx > left_idx:
                fwhm = wavelengths[right_idx] - wavelengths[left_idx]
            else:
                fwhm = 0
        else:
            fwhm = 0
        
        # Calculate AUC (Area Under Curve)
        if len(wavelengths) > 1:
            auc = np.trapezoid(intensities, wavelengths)
        else:
            auc = 0
        
        # Calculate SNR (simple version)
        noise_region = intensities < (max_intensity * 0.1)
        if np.any(noise_region) and len(intensities[noise_region]) > 1:
            noise_std = np.std(intensities[noise_region])
            snr = max_intensity / noise_std if noise_std > 0 else 0
        else:
            snr = 0
        
        # Update metrics dictionary
        self.metrics = {
            'peak_value': float(peak_value),
            'centroid': float(centroid),
            'max_intensity': float(max_intensity),
            'fwhm': float(fwhm),
            'snr': float(snr),
            'auc': float(auc)
        }
    
    def reset_metrics(self):
        """Reset all metrics to zero"""
        self.metrics = {
            'peak_value': 0,
            'centroid': 0,
            'max_intensity': 0,
            'fwhm': 0,
            'snr': 0,
            'auc': 0
        }
    
    def export_to_csv(self, parent_widget=None):
        """Export data points to CSV file"""
        if not self.data_points:
            if parent_widget:
                QMessageBox.warning(parent_widget, "No Data", "No data to save.")
            return False
        
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            parent_widget, 
            "Save Data", 
            "", 
            "CSV Files (*.csv)", 
            options=options
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Wavelength", "Intensity"])
                    for point in self.data_points:
                        writer.writerow(point)
                
                if parent_widget:
                    QMessageBox.information(parent_widget, "Success", f"Data saved to {filename}")
                return True
                
            except Exception as e:
                if parent_widget:
                    QMessageBox.critical(parent_widget, "Error", f"Failed to save file:\n{e}")
                return False
        
        return False
    
    def export_plot_as_png(self, plot_widget, parent_widget=None):
        """Export plot as PNG image"""
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            parent_widget, 
            "Export Graph", 
            "", 
            "PNG Files (*.png)", 
            options=options
        )
        
        if filename:
            try:
                exporter = pg.exporters.ImageExporter(plot_widget.plotItem)
                exporter.parameters()['width'] = 800
                exporter.export(filename)
                
                if parent_widget:
                    QMessageBox.information(parent_widget, "Exported", f"Graph saved as {filename}")
                return True
                
            except Exception as e:
                if parent_widget:
                    QMessageBox.critical(parent_widget, "Error", f"Failed to export graph:\n{e}")
                return False
        
        return False
    
    def get_metrics_text(self):
        """Get formatted text for all metrics"""
        return {
            'peak_value': f"PV is {self.metrics['peak_value']:.2f} nm",
            'centroid': f"C is {self.metrics['centroid']:.2f} nm",
            'max_intensity': f"MaxI is {self.metrics['max_intensity']:.0f}",
            'fwhm': f"FWHM is {self.metrics['fwhm']:.2f} nm",
            'snr': f"SNR is {self.metrics['snr']:.1f}",
            'auc': f"AUC is {self.metrics['auc']:.0f}"
        }
