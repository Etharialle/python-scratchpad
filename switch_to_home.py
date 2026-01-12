import ctypes
from ctypes import wintypes
#import time

# Windows Constants
VCP_INPUT_SELECT = 0x60

def set_monitor_input(input_value):
    # Load Windows libraries
    user32 = ctypes.windll.user32
    dxva2 = ctypes.windll.dxva2

    # 1. Find the Monitor Handles
    def foreach_monitor(hmonitor, hdc, lprect, lparam):
        # Get the number of physical monitors associated with the handle
        num_physical = wintypes.DWORD()
        if dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hmonitor, ctypes.byref(num_physical)):
            # Create an array to hold the physical monitor structures
            class PHYSICAL_MONITOR(ctypes.Structure):
                _fields_ = [("handle", wintypes.HANDLE), ("description", wintypes.WCHAR * 128)]
            
            monitors = (PHYSICAL_MONITOR * num_physical.value)()
            if dxva2.GetPhysicalMonitorsFromHMONITOR(hmonitor, num_physical, monitors):
                for phys in monitors:
                    # 2. Send the VCP Command (Code 60) to the monitor handle
                    dxva2.SetVCPFeature(phys.handle, VCP_INPUT_SELECT, input_value)
                    #time.sleep(0.1)
                    #dxva2.SetVCPFeature(phys.handle, VCP_INPUT_SELECT, input_value)
                    # Clean up handle
                    dxva2.DestroyPhysicalMonitor(phys.handle)
        return True

    # Monitor Enumeration Callback
    MONITOR_ENUM_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    user32.EnumDisplayMonitors(None, None, MONITOR_ENUM_PROC(foreach_monitor), 0)

# To use it:
if __name__ == "__main__":
    # Change to 15 for Home or 17 for Work!
    set_monitor_input(15) 
    print("Commands sent directly to Windows API!")