# Speckle Raspberry Pi
Python scripts for processing images with the Pi Camera in order to measure the heart-rate (HR) from a person using laser speckle techniques and optical fiber, including Bluetooth Low Energy (BLE) communication. We present here the main files to make the Raspberry Pi Zero W (with PiCamera connected) work with this purpose.

## Getting started

### bluez_components8.py
This code includes the setup for the BLE communication system, using [dbus](https://www.freedesktop.org/wiki/Software/dbus/), and creates all the classes concerning BLE Applications, Services and Characteristics.

### HR9.py
This file is intended to create the actual Application and Services that is going to be used.

### battery_management.py
This program works with the I2C bus for communicating with a [MAX17260](https://www.maximintegrated.com/en/products/power/battery-management/MAX17260.html) IC for battery management. In the main thread, it reads the battery level each minute. For the I2C communication it is used [smbus](http://wiki.erazor-zone.de/wiki:linux:python:smbus:doc).

### Speckle_Embedded_v8.py
This one is the master program. While it includes the processing mechanisms for extracting the HR value, consisting of one process for real-time signal acquisition and other one for signal processing, it also includes in its main thread the calling for all the other processes using [multiprocessing](https://docs.python.org/2/library/multiprocessing.html).

## Libraries

* [dbus](https://www.freedesktop.org/wiki/Software/dbus/)
* [smbus](http://wiki.erazor-zone.de/wiki:linux:python:smbus:doc)
* [Picamera v1.13](https://picamera.readthedocs.io/en/release-1.13/#)
* [SciPy](https://www.scipy.org/)
* [NumPy](https://www.numpy.org/)
* [Matplotlib](https://matplotlib.org/)
* [multiprocessing](https://docs.python.org/2/library/multiprocessing.html)

## Authors

* **Alvaro Robledo** 
* **Ignacio Sánchez**

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details
