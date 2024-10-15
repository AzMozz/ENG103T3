from max30102 import MAX30102
import hrcalc
import threading
import time
import numpy as np

class HeartRateMonitor(object):
    """
    A class that encapsulates the max30102 device into a thread
    """

    LOOP_TIME = 0.01

    def __init__(self, print_raw=False, print_result=False):
        self.bpm = 0
        self.spo2 = 0  # Add spo2 attribute to hold the latest reading
        self.print_raw = print_raw
        self.print_result = print_result
        self._thread = None
        self.is_running = False  # Track if the sensor is currently running
        self.sensor = None  # Initialize the sensor instance variable

    def run_sensor(self):
        self.sensor = MAX30102()  # Initialize sensor here
        ir_data = []
        red_data = []
        bpms = []

        while not self._thread.stopped:
            try:
                num_bytes = self.sensor.get_data_present()
                if num_bytes > 0:
                    while num_bytes > 0:
                        red, ir = self.sensor.read_fifo()
                        num_bytes -= 1
                        ir_data.append(ir)
                        red_data.append(red)
                        if self.print_raw:
                            print(f"{ir}, {red}")

                    while len(ir_data) > 100:
                        ir_data.pop(0)
                        red_data.pop(0)

                    if len(ir_data) == 100:
                        bpm, valid_bpm, spo2, valid_spo2 = hrcalc.calc_hr_and_spo2(ir_data, red_data)
                        if valid_bpm:
                            bpms.append(bpm)
                            while len(bpms) > 4:
                                bpms.pop(0)
                            self.bpm = np.mean(bpms)
                            if (np.mean(ir_data) < 50000 and np.mean(red_data) < 50000):
                                self.bpm = 0
                                self.spo2 = 0  # Reset spo2 if no finger is detected
                                if self.print_result:
                                    print("Finger not detected")
                            else:
                                if valid_spo2:
                                    self.spo2 = spo2
                                if self.print_result:
                                    print(f"BPM: {self.bpm}, SpO2: {self.spo2}")

                time.sleep(self.LOOP_TIME)

            except OSError as e:
                print(f"Error communicating with sensor: {e}")
                self.reset_sensor_and_leds()
                time.sleep(1)  # Pause briefly before trying again

            except Exception as e:
                print(f"Unexpected error: {e}")
                self.reset_sensor_and_leds()
                break  # Exit the loop on unexpected error

        self.sensor.shutdown()

    def reset_sensor_and_leds(self):
        """ Reset the sensor and LED states. """
        self.is_running = False
        if self.sensor is not None:  # Check if the sensor exists before calling shutdown
            self.sensor.shutdown()  # Ensure the sensor is turned off
        # Here, you would also reset your LED states if applicable, e.g.:
        # led_g.off()
        # led_r.off()

    def get_latest_reading(self):
        """Returns the latest BPM and SpO2 readings as a dictionary."""
        return {"bpm": self.bpm, "spo2": self.spo2}

    def start_sensor(self):
        self._thread = threading.Thread(target=self.run_sensor)
        self._thread.stopped = False
        self._thread.start()
        self.is_running = True  # Set the running flag

    def stop_sensor(self, timeout=2.0):
        self._thread.stopped = True
        self.bpm = 0
        self.spo2 = 0  # Reset spo2 when stopping
        self._thread.join(timeout)
        self.reset_sensor_and_leds()  # Ensure LED states are reset when stopping