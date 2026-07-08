import sys
try:
    import win32com.client
    word = win32com.client.Dispatch("Word.Application")
    word.Quit()
    print("Word COM is available!")
except Exception as e:
    print(f"Failed: {e}")
