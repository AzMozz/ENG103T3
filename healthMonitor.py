from gpiozero import LED, Button
from heartrate_monitor import HeartRateMonitor
from time import sleep, time
from datetime import datetime
import dropbox
import os

# Initialize components
led_g = LED(15)
led_r = LED(14)
button = Button(18)
hrm = HeartRateMonitor(print_result=True)

DROPBOX_APP_KEY = "	csjuutbmdc20u95"
DROPBOX_APP_SECRET = "1t15sf6afrgb6rt"
DROPBOX_ACCESS_TOKEN = "sl.B-1vol6pfXlwZt_xqmJprbYN77c8iVSNTMgyUKE5RwzLu7tz_RmBBipaqeHnupRoCXSTA9zjagSvmFlOMtWQeTwQ8wMWQz5g7VCnzk9khd82FQm3z2XX-Jx6hMmClfUdEbgClaf7qbKc"
DROPBOX_REFRESH_TOKEN = "lVfESq_Qgh0AAAAAAAAAAWr7uWN09iHPKUdIC72kHB8OVV_1YiRCx9CiIehisUOZ"

dbx = dropbox.Dropbox(
    oauth2_access_token=DROPBOX_ACCESS_TOKEN,
    oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
    app_key=DROPBOX_APP_KEY,
    app_secret=DROPBOX_APP_SECRET
)

SPO2_THRESHOLD = 90
BPM_THRESHOLD = 100
SENSOR_RUN_DURATION = 15

def blink_red_led(times=3, duration=0.5):
    for _ in range(times):
        led_r.on()
        sleep(duration)
        led_r.off()
        sleep(duration)

def stable_green_led():
    led_r.off()
    led_g.on()

def check_and_blink():
    readings = hrm.get_latest_reading()
    bpm = readings['bpm']
    spo2 = readings['spo2']
    if spo2 < SPO2_THRESHOLD or bpm > BPM_THRESHOLD:
        led_g.off()
        blink_red_led(times=3, duration=0.5)
    else:
        stable_green_led()

def log_data_to_file(file, readings):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    bpm = readings['bpm']
    spo2 = readings['spo2']
    file.write(f"{timestamp}, BPM: {bpm}, SpO2: {spo2}\n")
    file.flush()

def upload_to_dropbox_and_cleanup(filename):
    dropbox_folder_path = "/HealthData/"
    try:
        with open(filename, 'rb') as f:
            dbx.files_upload(f.read(), dropbox_folder_path + filename, mode=dropbox.files.WriteMode.overwrite)
        print(f"{filename} uploaded successfully.")
        os.remove(filename)
        print(f"{filename} deleted from local storage.")
    except Exception as e:
        print(f"Failed to upload {filename}: {e}")

def start_sensor_and_record():
    print("Starting sensor...")
    hrm.start_sensor()
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"sensor_data_{timestamp}.txt"

    with open(filename, 'w') as file:
        start_time = time()
        try:
            while time() - start_time < SENSOR_RUN_DURATION:
                readings = hrm.get_latest_reading()
                check_and_blink()
                log_data_to_file(file, readings)
                sleep(0.1)
        except Exception as e:
            print(f"Error while monitoring: {e}")
        finally:
            file.flush()
            print("Stopping Sensor")
            hrm.stop_sensor()
            print(f"Uploading {filename} to Dropbox...")
            upload_to_dropbox_and_cleanup(filename)
            led_g.off()
            led_r.off()


def main():
    print("Waiting for button press...")
    is_sensor_running = False  # Local flag for sensor state
    file = None  # Local file handler

    try:
        while True:
            if button.is_pressed:
                print("Button pressed, starting measurement...")
                start_sensor_and_record()  # Start the sensor and record data
                print("Measurement completed. Waiting for button press...")
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