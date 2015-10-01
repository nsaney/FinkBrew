import sys;
if sys.version_info[0] < 3:
    from Queue import Queue;
#
else:
    from queue import Queue;
#
import math;
import serial; # yay pySerial
import threading;
import time;

class ArduinoIO:
    """Used for reading and writing information with an Arduino."""
    
    #
    # Constants
    #
    
    #TIMEOUT_MS = 5000;
    
    
    #
    # Constructor / Instance fields
    #
    
    def __init__(self, _portId, _baudRate, _refreshRate, _isInTestMode, _newlineChar):
        """Constructor for ArduinoIO objects."""
        self.portId = _portId;
        self.baudRate = _baudRate;
        self.refreshRate = _refreshRate;
        self._isInTestMode = _isInTestMode;
        self.refreshSeconds = 1.0 / _refreshRate;
        self.refreshMillis = int(self.refreshSeconds * 1000);
        self.INPUT_NEWLINE_CHAR = _newlineChar
        
        self._isOpen = False;
        self._closeOnNextTick = False;
        
        self._readQueue = Queue();
        self._writeQueue = Queue();
        
        self._serialPort = None;
        if not self._isInTestMode:
            self._serialPort = serial.Serial(
                baudrate=self.baudRate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                #timeout=ArduinoIO.TIMEOUT_MS
            );
        #
        self._stopAfterNextRead = False;
        self._inputBuffer = [];
    #
    
    
    #
    # Instance Getters/Setters
    # 
    
    def isInTestMode(self): return self._isInTestMode;
    def isOpen(self): return self._isOpen;
    def setCloseOnNextTick(self): self._closeOnNextTick = True;
    
    
    #
    # Instance Methods
    # 
    
    def getNextTestReadData(self): 
        """[abstract] Gets the next testing read data."""
        return "";
    #
    
    def readsLeft(self):
        """Get the number of read objects currently in the read-queue."""
        return self._readQueue.qsize();
    #
    
    def readOne(self):
        """Read one data object parsed from the read-queue. Returns None if there is no data to read."""
        ro = None;
        readString = self.readOneString();
        ro = self.parse(readString);
        return ro;
    #
    
    def readOneString(self):
        """Read one string from the read-queue. Returns None if there is no data to read."""
        try: return self._readQueue.get_nowait();
        except: return None;
    #
    
    def parse(self, s):
        """[abstract] Parses a string into a Read Object."""
        return None;
    #
    
    def writeOne(self, wo):
        """Write one data object to the write-queue. Returns True if the write was successful."""
        writeString = self.format(wo);
        try: self._writeQueue.put_nowait(writeString);
        except: return False;
        else: return True;
    #
    
    def format(self, wo):
        """[abstract] Formats a Write Object as a string."""
        return None;
    #
    
    def open(self):
        """Open the connection to the Arduino."""
        openSuccessful = False;
        self._closeOnNextTick = False;
        if not self._isOpen:
            try:
                if not self._isInTestMode:
                    self._serialPort.port = self.portId;
                    self._stopAfterNextRead = False;
                    self._serialPort.open();
                    
                    readThread = threading.Thread(target=self.serialEventLoop, args=());
                    readThread.start();
                #
            #
            except Exception as ex:
                print ("Unable to open serial communication to the Arduino: " + str(ex));
            #
            else:
                # set openSuccessful if we get to this point
                openSuccessful = True;
                self._isOpen = True;
            #
            
            # start refresh thread
            refreshThread = threading.Thread(target=self.run, args=());
            refreshThread.start();
            
            # initialize subclass
            self.initSubclass();
        #
        return openSuccessful;
    #
    
    def initSubclass(self):
        """[virtual] Initialize subclass."""
        pass;
    #
    
    def run(self):
        """
        The refresh loop for this ArduinoIO object, which sends
        queued write information to the Arduino at the refresh interval.
        """
        timePreWrite = 0;
        timePostWrite = 0;
        timeWriteLength = 0;
        timeSleepLength = 0;
        
        try:
            while not self._closeOnNextTick:
                if self._isInTestMode:
                    # fake a read
                    fakeRead = self.getNextTestReadData();
                    try: self._readQueue.put_nowait(fakeRead);
                    except: pass;
                #
                
                # send all writes
                timePreWrite = time.time();
                self.sendWriteData();
                timePostWrite = time.time();
                timeWriteLength = timePostWrite - timePreWrite;
                
                # sleep for refresh time, or zero if sendWriteData took too long
                timeSleepLength = self.refreshSeconds - timeWriteLength;
                if timeSleepLength < 0: timeSleepLength = 0;
                time.sleep(timeSleepLength);
            #
        #
        except Exception as ex:
            print ("ArduinoIO refresh loop error: " + str(ex));
        #
        finally:
            self._close();
        #
    #
    
    def _close(self):
        """Close the connection to the Arduino."""
        closeSuccessful = False;
        if self._isOpen:
            self._isOpen = False;
            
            # set closeOnNextTick in case the refresh loop is still running
            self.closeOnNextTick = True;
            
            if not self._isInTestMode:
                if self._serialPort != None:
                    self._stopAfterNextRead = True;
                    self._serialPort.close();
                #
            #
        #
        return closeSuccessful;
    #
    
    def serialEventLoop(self):
        while not self._stopAfterNextRead:
            try:
                bytes = self._serialPort.read(1);
                if len(bytes) > 0:
                    b = bytes[0];
                    self.acceptReadData(b);
                #
            #
            except Exception as ex:
                print ("ArduinoIO serialEventLoop error: " + str(ex));
            #
        #
    #
    
    def acceptReadData(self, byteValue):
        """Accepts input from the Arduino."""
        if not self._isOpen: return;
        
        c = chr(byteValue);
        if c == self.INPUT_NEWLINE_CHAR:
            inputLine = "".join(self._inputBuffer);
            # using put_nowait() without try, so that any
            # exceptions will be logged to the console
            self._readQueue.put_nowait(inputLine);
            print (self._inputBuffer);
            self._inputBuffer = [];
        #
        else:
            self._inputBuffer.append(c);
        #
    #
    
    def sendWriteData(self):
        """Send all queued write data to the Arduino."""
        if not self._isOpen: return None;
        
        numberOfWrites = self._writeQueue.qsize();
        writes = [];
        for i in range(numberOfWrites):
            writes.append(self._writeQueue.get_nowait());
        #
        
        if self._isInTestMode:
            for w in writes:
                self.handleTestModeWrite(w);
            #
        #
        else:
            for w in writes:
                outputLine = w + self.INPUT_NEWLINE_CHAR;
                outputLineBytes = outputLine.encode();
                self._serialPort.write(outputLineBytes);
            #
        #
        
        return writes;
    #
    
    def handleTestModeWrite(self, w):
        """[virtual] Handles a test-mode write."""
        print ("Test-mode write: \"" + w + "\"");
    #
#