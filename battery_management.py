#!/usr/bin/python

import smbus
import pickle
from time import sleep

bus = smbus.SMBus(1)

DEVICE_ADDRESS    = 0x36
DesignCap         = 0x1F40


ADDRESS_HIBCFG    = 0xBA
ADDRESS_DESIGNCAP = 0x18
ADDRESS_ICHGTERM  = 0x1E
ADDRESS_VEMPTY    = 0x3A
ADDRESS_MODELCFG  = 0xDB
ADDRESS_STATUS    = 0x00
ADDRESS_REPCAP    = 0x05
ADDRESS_REPSOC    = 0x06
ADDRESS_TTE       = 0x11

def WriteRegister (reg,val):
    bus.write_word_data(DEVICE_ADDRESS,reg,val)

def ReadRegister (reg):
    return bus.read_word_data(DEVICE_ADDRESS,reg)

def WriteAndVerifyRegister (reg,val):
    attempt=0
    WriteRegister(reg,val)
    sleep(0.01)
    ValueRead = ReadRegister(reg)
    attempt+=1    

    while (val != ValueRead and attempt<3):
        WriteRegister(reg,val)
        sleep(0.01)
        ValueRead = ReadRegister(reg)
        attempt+=1 

def initialize():
    HibCFG = ReadRegister(ADDRESS_HIBCFG)
    WriteRegister(0x60,0x90)
    WriteRegister(ADDRESS_HIBCFG,0x00)
    WriteRegister(0x60,0x00)

    WriteRegister (ADDRESS_DESIGNCAP, DesignCap)
    WriteRegister (ADDRESS_ICHGTERM, 0x0280)
    WriteRegister (ADDRESS_VEMPTY, 0xA561)
    WriteRegister (ADDRESS_MODELCFG, 0x8000)

    while (ReadRegister(ADDRESS_MODELCFG) is 0x8000):
        sleep(0.01)
    
    WriteRegister(ADDRESS_HIBCFG, HibCFG)

    Status = ReadRegister(ADDRESS_STATUS)
    WriteAndVerifyRegister (ADDRESS_STATUS, Status&0xFFFD)

def save_parameters():
    Saved_RCOMP0        = ReadRegister(0x38)
    Saved_TempCo        = ReadRegister(0x39)
    Saved_FullCapRep    = ReadRegister(0x10)
    Saved_Cycles        = ReadRegister(0x17)
    Saved_FullCapNom    = ReadRegister(0x23)
    # Save elements into a file
    with open('battery_saved_parameters.pkl', 'w') as f:  # Python 3: open(..., 'wb')
        pickle.dump([Saved_RCOMP0, Saved_TempCo, Saved_FullCapRep, Saved_Cycles, Saved_FullCapNom], f)

def restore_parameters():
    with open('battery_saved_parameters.pkl') as f:  # Python 3: open(..., 'wb')
        Saved_RCOMP0, Saved_TempCo, Saved_FullCapRep, Saved_Cycles, Saved_FullCapNom = pickle.load(f)
    WriteAndVerifyRegister (0x38, Saved_RCOMP0)
    WriteAndVerifyRegister (0x39, Saved_TempCo)
    WriteAndVerifyRegister (0x10, Saved_FullCapRep)

    dQacc = (Saved_FullCapNom / 2)

    WriteAndVerifyRegister (0x46, 0x0C80)
    WriteAndVerifyRegister (0x45, dQacc)
    WriteAndVerifyRegister (0x17, Saved_Cycles)

def twos_comp(val, bits):
    """compute the 2's complement of int value val"""
    if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)        # compute negative value
    return val                         # return positive value as is


if __name__ == "__main__":

    while True:
        StatusPOR = ReadRegister(0x00) & 0x0002; #Read POR bit in Status Register
        #If StatusPOR=0, then go to measure the battery
        #If StatusPOR=1, then go to initialize
        
        if StatusPOR is 0:
            if ReadRegister(0x17)&0x0004:
                save_parameters()
            RepCap = ReadRegister(0x05)
            RepSOC = ReadRegister(0x06)
            TTE = ReadRegister(0x11)
            CURR = twos_comp(ReadRegister(0x0A),16) * 0.078125
            print ("Remaining " + str(RepSOC / 256) + " of capacity. Current = " + str(CURR))
            f = open('BAT_LEVEL.txt','w')
            f.write(str(RepSOC/256))
            f.close()        

        if StatusPOR is 2:
            restore_parameters()
            initialize()
        
        sleep (60)

    



