from gpiozero import LED, Button
from heartrate_monitor import HeartRateMonitor
from time import sleep, time
from datetime import datetime
import dropbox

# LEDs and button
led_g = LED(15)  # Green LED
led_r = LED(14)  # Red LED
button = Button(18)  # Push Button

# Heart Rate monitor instance
hrm = HeartRateMonitor(print_result=True)

# File handler (initialized when sensor starts)
file = None

# Threshold values
SPO2_THRESHOLD = 90
BPM_THRESHOLD = 100

# Duration for sensor to run (in seconds)
SENSOR_RUN_DURATION = 15  # Change this to your desired duration

DROPBOX_ACCESS_TOKEN = 'sl.B-eW308c2OG-fHjB8-U_8T3U-KBA_00avqN0N4dMDX7bFNcPDGxRpc9iZQNMS_vwOSUWQjGiAFgZXVOsQGgsZyyJQvZo4K4J8DGhZCt2nfayW9qIr0H-LUBatvvyffjGU8ehVIa2t0b7Mcmmm5t8'
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

# Handle Blinking Red LED
def blink_red_led(times=3, duration=0.5):
    for _ in range(times):
        led_r.on()
        sleep(duration)
        led_r.off()
        sleep(duration)

# Handle Stable Green LED
def stable_green_led():
    led_r.off()
    led_g.on()

# Check LED Status
def check_and_blink():
    readings = hrm.get_latest_reading()
    bpm = readings['bpm']
    spo2 = readings['spo2']

    # Blink red if SpO2 is below threshold or BPM is too high
    if spo2 < SPO2_THRESHOLD or bpm > BPM_THRESHOLD:
        led_g.off()
        blink_red_led(times=3, duration=0.5)
    else:
        stable_green_led()

def log_data_to_file(file, readings):
    """Log sensor data to the file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    bpm = readings['bpm']
    spo2 = readings['spo2']
    # Write to file: Timestamp, BPM, SpO2
    file.write(f"{timestamp}, BPM: {bpm}, SpO2: {spo2}\n")

def upload_to_dropbox():
    with open('sensor_data.txt', 'rb') as f:
        dbx.files_upload(f.read(), '/sensor_data.txt', mode=dropbox.files.WriteMode.overwrite)

def start_sensor_and_record():
    """Start the sensor and record data for a predetermined duration."""
    print("Starting sensor...")
    hrm.start_sensor()
    file = open('sensor_data.txt', 'a')  # Open file in append mode
    start_time = time()  # Record the start time
    try:
        while time() - start_time < SENSOR_RUN_DURATION:
            try:
                readings = hrm.get_latest_reading()  # Get sensor readings
                check_and_blink()  # Handle LED based on readings
                log_data_to_file(file, readings)  # Log readings to file
                sleep(0.1)  # Check every second
            except Exception as e:
                print(f"Error while monitoring: {e}")
    finally:
        # Ensure the sensor is stopped and the file is closed
        print('Stopping Sensor')
        hrm.stop_sensor()
        if file:
            file.close()  # Close the file
            print('Uploading data to Dropbox...')
            upload_to_dropbox()  # Upload the file to Dropbox
            # if uploaded successfully, print the success message
            if dbx.files_get_metadata('/sensor_data.txt'):
                print('Data uploaded successfully to Dropbox!')
        led_g.off()  # Turn off the Green LED
        led_r.off()  # Turn off the Red LED

def main():
    is_sensor_running = False  # Local flag for sensor state
    file = None  # Local file handler

    try:
        while True:
            if button.is_pressed:
                start_sensor_and_record()  # Start the sensor and record data
            else:
                sleep(0.1)  # Poll every 100ms for button press
    except KeyboardInterrupt:
        # Stop the sensor and cleanup on exit
        if is_sensor_running:
            hrm.stop_sensor()
        if file:
            file.close()
        print("Exiting program...")

if __name__ == "__main__":
    main()