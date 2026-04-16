import sys
import rclpy
from PyQt6.QtCore import QThread, pyqtSignal
from ros2.verifier_node import VerifierNode
from core.models import TopicInfo
from config.settings import ValidationStatus
import time

class Ros2Worker(QThread):
    # Signals to communicate with the GUI thread
    update_signal = pyqtSignal(dict) # Dictionary of results {topic_name: dict}
    error_signal = pyqtSignal(str)
    
    def __init__(self, topics: list[TopicInfo], hz_margin: float = 0.2, hz_window: float = 5.0):
        super().__init__()
        self.topics = topics
        self.hz_margin = hz_margin
        self.hz_window = hz_window
        self.is_running = False
        self.node = None

    def run(self):
        self.is_running = True
        try:
            if not rclpy.ok():
                rclpy.init()

            self.node = VerifierNode()
            self.node.set_hz_margin(self.hz_margin)
            self.node.set_hz_window(self.hz_window)
            self.node.update_topics_to_verify(self.topics)
            
            while self.is_running and rclpy.ok():
                # Process callbacks (non-blocking with small timeout)
                rclpy.spin_once(self.node, timeout_sec=0.5)
                
                # Get validation results from the node
                results = self.node.get_validation_results()
                
                # Emit to GUI
                self.update_signal.emit(results)
                
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            if self.node:
                self.node.destroy_node()
                self.node = None

    def stop(self):
        self.is_running = False
        self.wait() # Wait for thread to finish