import win32com.client
import traceback
try:
    wps = win32com.client.Dispatch("Kwps.Application")
    print("Successfully connected to Kwps.Application!")
    wps.Quit()
except Exception as e1:
    print(f"Kwps failed: {e1}")
    try:
        wps = win32com.client.Dispatch("wps.Application")
        print("Successfully connected to wps.Application!")
        wps.Quit()
    except Exception as e2:
        print(f"wps failed: {e2}")
