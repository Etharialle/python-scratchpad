def read_monitor_input():
    user32 = ctypes.windll.user32
    dxva2 = ctypes.windll.dxva2

    def foreach_monitor(hmonitor, hdc, lprect, lparam):
        num_physical = wintypes.DWORD()
        if dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hmonitor, ctypes.byref(num_physical)):
            class PHYSICAL_MONITOR(ctypes.Structure):
                _fields_ = [("handle", wintypes.HANDLE), ("description", wintypes.WCHAR * 128)]
            
            monitors = (PHYSICAL_MONITOR * num_physical.value)()
            if dxva2.GetPhysicalMonitorsFromHMONITOR(hmonitor, num_physical, monitors):
                for phys in monitors:
                    current_value = wintypes.DWORD()
                    max_value = wintypes.DWORD()
                    
                    # This is the "Read" command!
                    if dxva2.GetVCPFeatureAndVCPFeatureReply(
                        phys.handle, VCP_INPUT_SELECT, None, 
                        ctypes.byref(current_value), ctypes.byref(max_value)
                    ):
                        print(f"Monitor: {phys.description}")
                        print(f"Current Input Value: {current_value.value}")
                    
                    dxva2.DestroyPhysicalMonitor(phys.handle)
        return True

    MONITOR_ENUM_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    user32.EnumDisplayMonitors(None, None, MONITOR_ENUM_PROC(foreach_monitor), 0)

if __name__ == "__main__":
    read_monitor_input()