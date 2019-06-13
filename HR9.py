import dbus
import dbus.mainloop.glib
import multiprocessing
import time
import threading

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject

from bluez_components8 import *

mainloop = None


class HRAdvertisement(Advertisement):
    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid(UART_SERVICE_UUID)
        self.add_service_uuid(BatteryService.BATTERY_UUID)    
        self.include_tx_power = True

class HR_DC_Application(Application):
    def __init__(self, bus, q_HR, q_ctrl):
        Application.__init__(self, bus)
        self.add_service(UartService(bus,0,q_HR, q_ctrl))
        self.add_service(BatteryService(bus,1))



def register_ad_cb():
    """
    Callback if registering advertisement was successful
    """
    print('Advertisement registered')


def register_ad_error_cb(error):
    """
    Callback if registering advertisement failed
    """
    print('Failed to register advertisement: ' + str(error))
    mainloop.quit()


def register_app_cb():
    """
    Callback if registering GATT application was successful
    """
    print('GATT application registered')


def register_app_error_cb(error):
    """
    Callback if registering GATT application failed.
    """
    print('Failed to register application: ' + str(error))
    mainloop.quit()

def check_shdn(q_shdn):
    while True:
        if not q_shdn.empty():
            mainloop.quit()
            print('Down Process 3')
            sys.stdout.flush()
            return
        time.sleep(0.01)


def runMainloop():
    mainloop.run()
         

def runHR(q_HR, q_ctrl, q_shdn):
    global mainloop

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    # Get ServiceManager and AdvertisingManager
    service_manager = get_service_manager(bus)
    ad_manager = get_ad_manager(bus)

    # Create gatt services
    app = HR_DC_Application(bus,q_HR,q_ctrl)

    # Create advertisement
    test_advertisement = HRAdvertisement(bus, 0)

    mainloop = GObject.MainLoop()

    # Register gatt services
    service_manager.RegisterApplication(app.get_path(), {},
                                        reply_handler=register_app_cb,
                                        error_handler=register_app_error_cb)

    # Register advertisement
    ad_manager.RegisterAdvertisement(test_advertisement.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)    

    try:
        mainloopThread = threading.Thread(name='mainloop', target=runMainloop)
        mainloopThread.setDaemon(True)
        mainloopThread.start()

        inputThread = threading.Thread(name='input', target=check_shdn(q_shdn))
        inputThread.start()
    except KeyboardInterrupt:
        print('BYE')

    #try:
        #mainloop.run()
    #except KeyboardInterrupt:
        #display.clear()
        #display.write_display()
        #print('Down Process 3')


if __name__ == '__main__':
    runHR()
