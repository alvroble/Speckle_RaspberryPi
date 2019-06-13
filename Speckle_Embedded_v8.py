#!/usr/bin/python3

import multiprocessing
import threading
from picamera.array import PiRGBArray
from picamera import PiCamera
import numpy as np
import sys
import time
from scipy import signal as sig
import matplotlib.pyplot as plt
import math
import os
from HR9 import *
import RPi.GPIO as GPIO 

GPIO.setmode(GPIO.BCM)



def welch_bpm(data,Fs):
    F, Pxx = sig.welch(data,fs=Fs, nperseg=20*Fs)
    F = 60*F
    index = np.argmax(Pxx)
    bpm = F[index]
    return bpm
    

def image_acq(queue_proc, queue_ctrl_BLE, queue_shdn, tlim, buffer):
  
    while True:
        print("buffer: ", buffer)
        if buffer == 0:
            while queue_ctrl_BLE.empty() and queue_shdn.empty():
                time.sleep(0.1) 
            if not queue_ctrl_BLE.empty():            
                receive_ctrl = queue_ctrl_BLE.get()
                print('Acquisition is ON: ' + str(receive_ctrl))
                if receive_ctrl is 10:
                    buffer = 1
            if not queue_shdn.empty():            
                print('Down Process 1')
                sys.stdout.flush()
                break
            

        elif buffer == 1:
            if not queue_shdn.empty():            
                print('Down Process 1')
                sys.stdout.flush()
                break
            with PiCamera() as camera:
                # initialize the camera and grab a reference to the raw camera capture
                W = 304
                H = 304
                camera.resolution = (W, H)
                camera.exposure_compensation = -15
                #camera.start_preview()
                camera.zoom = (0.30,0.30,0.4,0.4)
                camera.awb_mode = 'off'
                camera.awb_gains = (0.4,0.4)
                camera.brightness = 20
                camera.contrast = 100
                camera.saturation = 0
                Fs = 10
                camera.framerate = Fs
                rawCapture = PiRGBArray(camera, size=(W, H))
                image = np.zeros((W, H, 3), np.uint8)
                signal = 0
                max_signal = 0
                min_signal = 0
                t = 0
                n = 200
                total_signal = np.empty((0,),dtype=int)

                # allow the camera to warmup
                time.sleep(10)
                i = 0 
                tt2 = time.time()
                t = 0
                end = False
                print('Starting acquisition !')
                # capture frames from the camera
                for frame in camera.capture_continuous(rawCapture, format="rgb", use_video_port=True):
                    # grab the raw NumPy array representing the image, then initialize the timestamp
                    # and occupied/unoccupied text
                    fr = frame.array
                    tt = time.time()
                    
                    this_frame = fr[:,:,0]
                    signal = (this_frame.sum())/(W*H)
                    signal=np.power(signal,7)
                    #print(signal)
                    total_signal = np.append(total_signal, signal)
                    t = i / Fs
                    
                    elapsed = time.time() - tt
                    if elapsed > 0.1:
                        print('Bad time: ' + str(elapsed))

                    # clear the stream in preparation for the next frame
                    rawCapture.truncate(0)

                    #print(j)
                    queue_proc.put([signal, t, i, end])
                    if not queue_shdn.empty():
                        break
                        
                    if t >= tlim:
                        end = True
                        print('Ending image acquisition')
                        queue_proc.put([signal, t, i, end])
                        buffer=0
                        break

                    elif not queue_ctrl_BLE.empty():
                        if queue_ctrl_BLE.get() == 20:
                            end = True
                            print('Ending image acquisition')
                            queue_proc.put([signal, t, i, end])
                            buffer=0
                            break     
                    i += 1

                camera.close()


def data_proc(queue_proc, queue_HR_BLE,queue_shdn):
    """ 
    function to print the messages received from other 
    end of pipe 
    """
    Fs = 10
    n = 20*Fs # For 20 seconds each time
    tt = time.time()
    signal = np.zeros(n)
    t = np.zeros(n)
    
    ended = False
    
    all_the_signal = np.empty((0,),dtype=float)
    mean_bpm = np.empty((0,),dtype=float)     
        
    # Butterworth
    nyq_rate = Fs / 2.0
    N, Wn = sig.buttord([0.8/nyq_rate , 3/nyq_rate ], [0.6/nyq_rate , 3.5/nyq_rate ], 1, 60 ) #[48,180][36,240] Hz
    b, a  = sig.butter(N, Wn, btype='bandpass')
    print("N, WN = "+ str(N)+ ", "+str(Wn))
   
    while True:
        if not queue_shdn.empty():
            print('Down Process 2')
            sys.stdout.flush()
            break
        elapsed = time.time() - tt
        time.sleep(0.1)
        if not queue_proc.empty(): 
            msg = queue_proc.get()
            if msg == -1:
                break
            elif msg[3] == False:
                
                if msg[2] < n:
                    signal[msg[2]] = msg[0]
                    t[msg[2]] = msg[1]
                    all_the_signal = np.append(all_the_signal, msg[0])
                    
                else:
                    if msg[2] == n:
                        print('Hey I\'m processing!')
                    signal[:-1] = signal[1:]
                    signal[-1] = msg[0]
                    all_the_signal = np.append(all_the_signal, msg[0])
                    #print('Value added: ' + str(signal[-1]))
                    
                    t[:-1] = t[1:]
                    t[-1] = msg[1]
                
                    if elapsed > 2:    
                        print('Time: ' + str(t[-1]))
                        
                        # quitting bad values
                        
                        # signal filtering and detrend
                        signal_p = signal - np.mean(signal)
                        dsignal = sig.detrend(signal_p, bp=[n/4,n/2,3*n/4])
                        
                        # 1. Butterworth
                        filtered_Butter = sig.filtfilt(b,a,dsignal)
                        
                        
                        # ----> Estimation 3: Welch PSD
                        try:
                            # 1. Butterworth
                            bpm_Butter = welch_bpm(filtered_Butter,Fs)
                            print('\tEstimation (Pwelch-Butter): ' + str(bpm_Butter))                       
                            mean_bpm = np.append(mean_bpm, bpm_Butter)
                            queue_HR_BLE.put(int(bpm_Butter))
                        except:
                            print('Error in Estimation!!')
                        
                        tt = time.time()

            else:
                print('End. Final value (Butter-3): ' + str(np.mean(mean_bpm)))
                #ended = False

        time.sleep(0.001)

def check_shdn(queue_shdn):
    f = open('/home/pi/SHDN.txt','w')
    f.write(str(0))
    f.close()
    while True:
        f = open('/home/pi/SHDN.txt','r')
        shdn = int(f.read()) 
        #print('shdn vale:'+str(shdn))       
        f.close()
        if shdn == 1:
            print('Shutting down Raspberry Pi')
            queue_shdn.put(shdn)
            break
        time.sleep(0.01)


if __name__ == "__main__":
    #sys.stdout = open('/home/pi/Speckle.log','w')
    # creating a pipe 
    queue_proc = multiprocessing.Queue()
    queue_ctrl_BLE = multiprocessing.Queue()    
    queue_HR_BLE = multiprocessing.Queue()
    queue_shdn = multiprocessing.Queue()
    
    tlim = 600
    buffer = 0
    
        
    # creating new processes 
    p1 = multiprocessing.Process(target=image_acq, args=(queue_proc, queue_ctrl_BLE, queue_shdn, tlim, buffer))
    p2 = multiprocessing.Process(target=data_proc, args=(queue_proc, queue_HR_BLE, queue_shdn))
    p3 = multiprocessing.Process(target=runHR, args=(queue_HR_BLE, queue_ctrl_BLE, queue_shdn))
    p4 = multiprocessing.Process(target=check_shdn, args=(queue_shdn,))

    # running processes 
    p4.start()
    p3.start()
    p2.start()
    p1.start()

    # wait until processes finish 
    p1.join()
    p2.join()
    p3.join()
    p4.join()
    
    
    print('BYE !! ')
    sys.stdout.flush()
    sys.stdout.close()
    os.system("sleep 5s")
    os.system("sudo shutdown now")
    #GPIO.setup(19,GPIO.OUT)
    #GPIO.output(19,False)
