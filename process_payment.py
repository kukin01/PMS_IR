import serial
import pandas as pd
from datetime import datetime
import time

SERIAL_PORT = '/dev/ttyACM0'  # Update as needed
BAUD_RATE = 9600
CSV_FILE = 'plates_log.csv'
PARKING_RATE_PER_HOUR = 200  # RWF

def load_csv():
    return pd.read_csv(CSV_FILE)

def save_csv(df):
    df.to_csv(CSV_FILE, index=False)

def calculate_due(entry_time_str, exit_time):
    entry_time = datetime.strptime(entry_time_str, '%Y-%m-%d %H:%M:%S')
    duration = exit_time - entry_time
    hours = duration.total_seconds() / 3600
    hours_rounded = int(hours) if hours == int(hours) else int(hours) + 1  # Round up partial hours
    due = hours_rounded * PARKING_RATE_PER_HOUR
    return due, hours_rounded

def main():
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Wait for Arduino reset

    print("Waiting for plate number from Arduino...")

    while True:
        line = ser.readline().decode('utf-8').strip()
        if line.startswith("PLATE:"):
            plate = line.split("PLATE:")[1].strip()
            print(f"Received plate: {plate}")

            df = load_csv()
            row_idx = df.index[df['Plate Number'] == plate].tolist()

            if not row_idx:
                print(f"Plate {plate} not found in CSV.")
                ser.write(b"STATUS:NOT_FOUND\n")
                continue

            idx = row_idx[0]
            status = df.at[idx, 'Payment Status']
            entry_time_str = df.at[idx, 'Timestamp']

            if status == 1:
                print(f"Plate {plate} already paid.")
                ser.write(b"STATUS:PAID\n")
                continue

            # status == 0, unpaid - process payment
            exit_time = datetime.now()
            due_amount, hours_parked = calculate_due(entry_time_str, exit_time)

            print(f"Hours parked: {hours_parked}, Due amount: {due_amount} RWF")

            # Update CSV with exit_time and due_amount, keep status=0 (unpaid)
            df.at[idx, 'Exit Time'] = exit_time.strftime('%Y-%m-%d %H:%M:%S')
            df.at[idx, 'Due Amount'] = due_amount
            save_csv(df)

            # Send due amount to Arduino for deduction
            ser.write(f"DUE:{due_amount}\n".encode())
            print("Sent due amount to Arduino, waiting for confirmation...")

            # Wait for Arduino confirmation: either "DONE" or "INSUFFICIENT"
            confirmation = ser.readline().decode('utf-8').strip()
            if confirmation == "DONE":
                print("Payment confirmed by Arduino. Updating status to PAID.")
                df.at[idx, 'Payment Status'] = 1  # Paid
                save_csv(df)
                ser.write(b"STATUS:PAID\n")
            elif confirmation == "INSUFFICIENT":
                print("Insufficient balance on card. Payment failed.")
                ser.write(b"STATUS:INSUFFICIENT\n")
            else:
                print("Payment not confirmed by Arduino.")
                ser.write(b"STATUS:FAILED\n")

        time.sleep(0.1)

if __name__ == "__main__":
    main()