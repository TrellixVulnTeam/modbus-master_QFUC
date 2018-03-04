'''
Pymodbus Synchronous Client Examples
--------------------------------------------------------------------------
The following is an example of how to use the synchronous modbus client
implementation from pymodbus.
It should be noted that the client can also be used with
the guard construct that is available in python 2.5 and up::
    with ModbusClient('127.0.0.1') as client:
        result = client.read_coils(1,10)
        print result
'''
#---------------------------------------------------------------------------# 
# import the various server implementations
#---------------------------------------------------------------------------# 
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from ConfigReader import ConfigReader
import MySQLdb
import time
import sys
from Client import Client, DummyClient
#---------------------------------------------------------------------------#
# read config
#---------------------------------------------------------------------------#
configReader = ConfigReader("config.ini")
#---------------------------------------------------------------------------#
# validate login credentials
#---------------------------------------------------------------------------#

import getopt
login = ''
password = ''
createUser = None
offline = True
try:
    opts, args = getopt.getopt(sys.argv,"hcl:p:",["login=","password="])
except getopt.GetoptError:
    print('modbus.py -l <login> -o <password>')
    print('modbus.py -c #creates new user interactively')
    sys.exit(2)
for opt, arg in opts:
    if(opt == '-h'):
        print('modbus.py #runs in offline mode')
        print('modbus.py -l <login> -o <password>')
        print('modbus.py -c #creates new user interactively')
        sys.exit()
    elif(opt == "-c"):
        offline = False
        createUser = True
    elif(opt in ("-l","--login")):
        offline= False
        login = arg
    elif(opt in ("-p","--password")):
        offline = False
        password = arg
server = configReader.GetSectionMap('SERVER')
clienthtp = DummyClient(server['ip'],server['port'])
if(not offline):
    clienthtp = Client(server['ip'],server['port'])
if(createUser is not None):
    clienthtp.RegisterUser()
    sys.exit()
else:
    if(not clienthtp.LogIn(login,password)):
        sys.exit(1)
#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)
#---------------------------------------------------------------------------# 
# choose the client you want
#---------------------------------------------------------------------------# 

serial = configReader.GetSectionMap("SERIAL");
client = ModbusClient(method='rtu', port=serial["port"], timeout=int(serial["timeout"]),
                      baudrate = int(serial["baud"]), bytesize = int(serial["databits"]),
                      stopbits = int(serial["stopbits"]), parity = serial["parity"],
                      rtscts = int(serial["rtscts"]))
print("connecting to %s..."%serial['port'])
if(client.connect()):
    print("connected")
else:
    print("Unable to establish connection via {0}", serial["port"])
    sys.exit(1)
#---------------------------------------------------------------------------# 
# specify slave to query
#---------------------------------------------------------------------------# 
def ReadRegisters(client,unit_,address,nrOfReg):
    log.debug("Read input registers")
    #rr= client.write_register(0,20, unit=0x01)
    #rr = client.read_holding_registers(0, 1, unit=0x01)
    #rr = client.write_coils(1999, [True,True,True,True,True],unit=0x01)
    #time.sleep(4)
    bb = client.read_coils(1999,1,unit=0x01)
    if(bb is None):
        print("Read timed out for slave nr {0}",unit_)
        return
    rr = client.read_input_registers(address, nrOfReg, unit=0x01)
    if(rr is None):
        print("Read timed out for slave nr {0}",unit_)
        return
    if(rr.function_code >= 0x80):   # test that we are not an error
        print('Invalid response from:'+str(address)+'. Error code: '+hex(rr.function_code))
        return
    print(rr.registers)
    try:
        data = {'stationID': unit_, 'temperature': (rr.registers[0]/10), 'humidity': (rr.registers[1]/10), 'lux':rr.registers[2], 'soil':rr.registers[3],
                'battery': rr.registers[4], 'co2': rr.registers[5]}
    except Exception as e:
        print("Response was broken")
        return
    finally:
        log.debug(data)
        clienthtp.SendReadings(data)
#---------------------------------------------------------------------------#
# Initialize slaves according to slaves.txt
#---------------------------------------------------------------------------#
from SlaveLoader import SlaveLoader
sloader = SlaveLoader()
slaves = sloader.LoadFromFile("slaves.txt")
for slave in slaves:
    slave.SetCallback(ReadRegisters,client)
#---------------------------------------------------------------------------#
# Run tick forever
#---------------------------------------------------------------------------#
import time
while True:
    timeBegin = time.time()
    for slave in slaves:
        slave.Tick()
    timeElapsed = time.time() - timeBegin
    if(timeElapsed<=1):
        time.sleep(1-timeElapsed)
#---------------------------------------------------------------------------# 
# close the client
#---------------------------------------------------------------------------# 
client.close()
