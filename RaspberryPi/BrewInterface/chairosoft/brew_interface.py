import sys;
if sys.version_info[0] < 3:
    from Tkinter import *;
    import tkFont;
    import tkFileDialog;
    import tkMessageBox;
#
else:
    from tkinter import *;
    import tkinter.font as tkFont;
    import tkinter.filedialog as tkFileDialog;
    import tkinter.messagebox as tkMessageBox;
#
from enum import Enum;  #sudo apt-get install python-enum
import random;
import colorsys;
import time;
import math;
import xml.etree.ElementTree as ElementTree;
import os;
import datetime;
from chairosoft.arduino import ArduinoIO;
from chairosoft.pyutils import *;
from chairosoft.tkutils import *;


# Constants
APP_TITLE = "FinkBrew 0.4";
PORT_ID = 'COM81';
BAUD_RATE = 115200;
REFRESH_RATE = 5; #Hz
USES_TEST_MODE = True;
INPUT_NEWLINE_CHAR = '\r';

# PORT_NAMES 
# "/dev/ttyACM0" # Mega on Raspberry Pi
# "COM3"         # Mega on Windows
# "COM81"        # com0com on Windows
# "COM6"         # Uno on Windows

BOIL_ADDITION_NOTIFICATION_MINUTES = [5];
BOIL_ADDITION_NOTIFICATION_MINUTES.sort(key=lambda x: -x);
BOIL_ADDITION_NOTIFICATION_SECONDS = [(idx, 60 * minutes) for (idx, minutes) in enumerate(BOIL_ADDITION_NOTIFICATION_MINUTES)]

MASH_TEMP_TOLERANCE_UP = 9.0; #F
MASH_TEMP_TOLERANCE_DOWN = -2.1; #F

CC.gray_main = "#dcdcdc";
CC.gray_menu = "#bcbcbc";

CONTAINER_HEIGHT = 300;
CONTAINER_BORDER_WIDTH = 1;
CONTAINER_MARGIN_BOTTOM = 5;
CONTAINER_TEXT_SEPARATION = 0;
CONTAINER_INNER_HEIGHT = CONTAINER_HEIGHT - 2*CONTAINER_BORDER_WIDTH - CONTAINER_MARGIN_BOTTOM - CONTAINER_TEXT_SEPARATION;
LEVEL_WIDTH = 180;
TEMP_BAR_WIDTH = 120;
SPACING = 50;



###########################
###                     ###
###  Class Definitions  ###
###                     ###
###########################

class BrewPreferences:
    filenamesToCheck = ["resources/BrewPreferences.xml"];
    fname = "";
    
    @staticmethod
    def init():
        try:
            BrewPreferences.areValid = False;
            for fname in BrewPreferences.filenamesToCheck:
                if os.path.isfile(fname):
                    BrewPreferences.fname = fname;
                    break;
                #
            #
            if BrewPreferences.fname:
                BrewPreferences.xtree = ElementTree.parse(BrewPreferences.fname);
                xroot = BrewPreferences.xtree.getroot();
                xnotification = xroot.find(".//Notification");
                
                BrewPreferences.xnotificationSmtpServer = xnotification.find("SmtpServer");
                BrewPreferences.notificationSmtpServer = BrewPreferences.xnotificationSmtpServer.text;
                BrewPreferences.xnotificationSmtpUsername = xnotification.find("SmtpUsername");
                BrewPreferences.notificationSmtpUsername = BrewPreferences.xnotificationSmtpUsername.text;
                BrewPreferences.xnotificationSmtpPassword = xnotification.find("SmtpPassword");
                BrewPreferences.notificationSmtpPassword = BrewPreferences.xnotificationSmtpPassword.text;
                BrewPreferences.xnotificationFromAddress = xnotification.find("FromAddress");
                BrewPreferences.notificationFromAddress = BrewPreferences.xnotificationFromAddress.text;
                BrewPreferences.xnotificationToAddresses = xnotification.find("ToAddresses");
                BrewPreferences.notificationToAddresses = [xe.text for xe in BrewPreferences.xnotificationToAddresses];
                
                # if we get here okay, brew preferences are valid
                BrewPreferences.areValid = True;
            #
        #
        except Exception as ex:
            BrewPreferences.exception = ex;
            print ("Error reading Brew Preferences: " + str(ex));
        #
        print ("Brew Preferences loaded successfully." if BrewPreferences.areValid else "BrewPreferences not loaded.");
    #
    
    @staticmethod
    def saveXmlFile():
        BrewPreferences.xnotificationSmtpServer.text = BrewPreferences.notificationSmtpServer;
        BrewPreferences.xnotificationSmtpUsername.text = BrewPreferences.notificationSmtpUsername;
        BrewPreferences.xnotificationSmtpPassword.text = BrewPreferences.notificationSmtpPassword;
        BrewPreferences.xnotificationFromAddress.text = BrewPreferences.notificationFromAddress;
        BrewPreferences.xnotificationToAddresses.clear();
        for toAddress in BrewPreferences.notificationToAddresses:
            ElementTree.SubElement(BrewPreferences.xnotificationToAddresses, "ToAddress").text = toAddress;
        #
        return BrewPreferences.xtree.write(BrewPreferences.fname, encoding="UTF-8", xml_declaration=True);
    #
#
BrewPreferences.init();


class CustomFonts:
    """Static-ish class for font definitions."""
    title = ("Arial", 24, "bold");
    button = ("Arial", 18, "bold");
    label = ("Arial", 21, "bold");
    labelMedium = ("Arial", 17, "bold");
    labelSmall = ("Arial", 13, "bold");
    text = ("Arial", 18, "normal");
    textMedium = ("Arial", 14, "normal");
    textSmall = ("Arial", 10, "normal");
    monoLargeBold = ("Courier", 18, "bold");
    monoLarge = ("Courier", 18, "normal");
    monoMediumBold = ("Courier", 14, "bold");
    monoMedium = ("Courier", 14, "normal");
    monoSmallBold = ("Courier", 10, "bold");
    monoSmall = ("Courier", 10, "normal");
#

class BrewStep(Enum):
    ST_MENU         = 0; 
    ST_READY        = 1; # no movement
    ST_FILL         = 2; # filling HLT with water
    ST_STRIKE       = 3; # heating HLT to Strike Temp
    ST_MASH_IN      = 4; # actual "Strike" or "Infusion" i.e., transfer from HLT to MLT
    ST_MASH         = 5; # pumping wort through heat exchange (in HLT)
    ST_MASH_OUT     = 6; # same config as ST_MASH (don't use)
    ST_SPARGE       = 7; # from bottom of MLT, recirc for heat exchange, rinse with sparge water
    ST_BOIL         = 8; # no movement
    ST_STEEP        = 9; # whirlpool
    ST_COOL         = 10; # same config as ST_FILLFERM (don't use)
    ST_FILLFERM     = 11; # drain to fermentor
    ST_DONE         = 12; # no movement
    ST_DRAIN        = 13; 
    ST_DRAIN_MLT    = 14; 
    ST_DRAIN_HLT    = 15; 
    ST_CIP          = 16; # clean-in-place phase
    ST_ERROR        = 666;
#

def parseBrewStepOrDefault(s, defaultBrewStepValue):
    result = defaultBrewStepValue;
    try: result = BrewStep(int(s));
    except Exception as ex: print ("invalid parse: " + str(ex));
    return result;
#

def parseIntOrDefault(s, defaultIntValue):
    result = defaultIntValue;
    try: result = int(s);
    except Exception as ex: print ("invalid parse: " + str(ex));
    return result;
#

def parseFloatOrDefault(s, defaultFloatValue):
    result = defaultFloatValue;
    try: result = float(s);
    except Exception as ex: print ("invalid parse: " + str(ex));
    return result;
#

class BrewReadObject:
    def __init__(self, s):
        self.__originalData = s;
        
        step = BrewStep.ST_ERROR;
        hpt = 0;
        mpt = 0;
        bpt = 0;
        hlv = 0;
        mlv = 0;
        blv = 0;
        
        try:
            if s != None:
                splitValues = s.split(";");
                for entry in splitValues:
                    splitEntryValues = entry.split(":");
                    entryName = splitEntryValues[0];
                    entryValue = splitEntryValues[1];
                    if entryName == "stp": step = parseBrewStepOrDefault(entryValue, step);
                    elif entryName == "hpt": hpt = parseFloatOrDefault(entryValue, hpt);
                    elif entryName == "mpt": mpt = parseFloatOrDefault(entryValue, mpt);
                    elif entryName == "bpt": bpt = parseFloatOrDefault(entryValue, bpt);
                    elif entryName == "hlv": hlv = parseFloatOrDefault(entryValue, hlv);
                    elif entryName == "mlv": mlv = parseFloatOrDefault(entryValue, mlv);
                    elif entryName == "blv": blv = parseFloatOrDefault(entryValue, blv);
                #
            #
        #
        except Exception as ex:
            print (ex);
        #
        
        self.brewStep = step;
        self.tempHlt = hpt;
        self.tempMlt = mpt;
        self.tempBk = bpt;
        self.levelHlt = hlv;
        self.levelMlt = mlv;
        self.levelBk = blv;
    #
    
    def originalData(self): 
        return self.__originalData;
    #
#

class BrewWriteObject:
    def __init__(self, _step, _params={}):
        self.step = _step;
        self.params = _params;
        self.allParams = self.params.copy();
        self.allParams["stp"] = self.step.value;
        self.formatted = ";".join(["%s:%s" % (k,v) for (k,v) in self.allParams.items()]);
    #
#

class BrewIO(ArduinoIO):
    """An ArduinoIO that uses BrewReadObject and BrewWriteObject."""
    def __init__(self, _portId, _baudRate, _refreshRate, _isInTestMode, _newlineChar):
        ArduinoIO.__init__(self, _portId, _baudRate, _refreshRate, _isInTestMode, _newlineChar);
        self.testStep = BrewStep.ST_READY;
        self.testHpt = 72.0;
        self.testMpt = 72.0;
        self.testBpt = 72.0;
        self.testHlv = 0.0;
        self.testMlv = 0.0;
        self.testBlv = 0.0;
    #
    
    def initSubclass(self): 
        """[override] Initialize subclass."""
        pass;
    #
    
    def getNextTestReadData(self): 
        """[override] Gets the next testing read data."""
        # self.testHpt += random.randrange(-2, 3);
        # self.testMpt += random.randrange(-2, 3);
        # self.testBpt += random.randrange(-2, 3);
        # self.testHlv += random.randrange(-5, 6) * 0.001;
        # self.testMlv += random.randrange(-5, 6) * 0.001;
        # self.testBlv += random.randrange(-5, 6) * 0.001;
        return \
            "__TEST:__DATA;stp:%s;hpt:%s;mpt:%s;bpt:%s;hlv:%s;mlv:%s;blv:%s" \
            % (self.testStep.value, self.testHpt, self.testMpt, self.testBpt, self.testHlv, self.testMlv, self.testBlv);
    #
    
    def parse(self, s):
        """[override] Parses a string into a Read Object."""
        return BrewReadObject(s);
    #
    
    def format(self, wo):
        """[override] Formats a Write Object as a string."""
        return wo.formatted;
    #
#

class BrewActionItem:
    # tsp is temperature set point in degrees Fahrenheit
    # amt is liquid transfer volume in liters
    def __init__(self, brewStep, durationSeconds=0, tsp=-1, amt=-1, title="", message=""):
        self.brewStep = brewStep;
        self.durationSeconds = durationSeconds;
        params = {};
        if tsp > -1: params["tsp"] = "%.1f" % tsp;
        if amt > -1: params["amt"] = "%.1f" % amt;
        self.writeObject = BrewWriteObject(self.brewStep, params);
        
        self.title = title;
        self.message = message;
        
        self.onActionStart = (lambda: None);
        self.onActionExecuting = (lambda ro: None);
    #
    def __str__(self):
        result  = "[[ \n";
        result += "  title = %r \n" % self.title;
        result += "  message = %r \n" % self.message;
        if self.durationSeconds > 0:
            result += "  duration = %s \n" % convertSecondsToMmSs(self.durationSeconds, "%02d");
        #
        result += "  brewStep = %r \n" % self.brewStep;
        result += "  writeObject = %r \n" % self.writeObject.formatted;
        result += "]]";
        return result;
    #
#

class AmountType(Enum):
    none = ("none", );
    item = ("items", );
    kilogram = ("kg", );
    ounce = ("oz", );
    liter = ("L", );
    teaspoon = ("tsp", );
    def __init__(self, unit):
        self.unit = unit;
    #
#

class BrewBoilAddition:
    def __init__(self, type, name, use, time, amount, amountType):
        self.type = type;
        self.name = name;
        self.use = use;
        self.time = time;
        self.amount = amount;
        self.amountType = amountType;
        if self.amountType == AmountType.kilogram:
            self.amount = convertKgToOz(self.amount);
            self.amountType = AmountType.ounce;
        #
        elif self.amountType == AmountType.liter:
            self.amount = convertLtoTsp(self.amount);
            self.amountType = AmountType.teaspoon;
        #
        self.xElement = ElementTree.Element("BrewBoilAddition");
        ElementTree.SubElement(self.xElement, "Type").text = self.type;
        ElementTree.SubElement(self.xElement, "Name").text = self.name;
        ElementTree.SubElement(self.xElement, "Use").text = self.use;
        ElementTree.SubElement(self.xElement, "Time").text = self.time;
        ElementTree.SubElement(self.xElement, "Amount").text = self.amount;
        ElementTree.SubElement(self.xElement, "Unit").text = self.amountType.unit;
        self.notificationMessage = "Add %.2f %s %s" % (self.amount, self.amountType.unit, self.name);
    #
    def __str__(self):
        return "[[name=%r, use=%r, time=%r, amount=%r, amountType=%r]]" \
            % (self.name, self.use, self.time, self.amount, self.amountType.unit);
    #
#

class NotificationFrame():
    __notificationCount = 0;
    def __init__(self, parent, message, secondsMax):
        self.rowNum = NotificationFrame.__notificationCount;
        NotificationFrame.__notificationCount += 1;
        
        self._timeLabel = Label(parent, bg=parent["bg"], fg=CC.black, font=CustomFonts.textMedium, text="[time]");
        
        self._notificationsSent = 0;
        self._acknowledged = False;
        def ackButtonCommand():
            self._acknowledged = True;
            self._timeLabel.grid_forget();
            self._ackButton.grid_forget();
            self._messageLabel.grid_forget();
        #
        self._ackButton = Button(parent, state=DISABLED, command=ackButtonCommand, bd=2, relief=FLAT, bg=CC.gray, fg=CC.black, text="Ack", font=CustomFonts.textMedium);
        
        self._message = message;
        self._messageLabel = Label(parent, bg=parent["bg"], fg=CC.black, font=CustomFonts.textMedium, text=message);
        
        self._secondsMax = secondsMax;
        self._secondsLeft = secondsMax;
    #
    
    def show(self):
        self._timeLabel.grid(row=self.rowNum, column=0, sticky=E);
        self._ackButton.grid(row=self.rowNum, column=1, sticky=(W,E), padx=2, pady=2);
        self._messageLabel.grid(row=self.rowNum, column=2, sticky=W);
    #
    
    def setTimeLeftOnBoil(self, secondsLeftOnBoil):
        if self._acknowledged: 
            return;
        #
        
        self._secondsLeft = secondsLeftOnBoil - self._secondsMax;
        if (self._secondsLeft <= 0):
            self._secondsLeft = 0;
            self._ackButton.config(state=NORMAL, relief=RAISED, bg=CC.blue, );
        #
        timeText = convertSecondsToMmSs(self._secondsLeft);
        self._timeLabel.config(text=timeText);
        
        ## the following is not done the most efficient way, but it is not a lot of overhead
        for (idx, seconds) in BOIL_ADDITION_NOTIFICATION_SECONDS:
            if self._notificationsSent == idx and self._secondsLeft <= seconds:
                self.sendNotification();
                print ("\a");
                break;
            #
        #
    #
    
    def sendNotification(self):
        if self._acknowledged: 
            return;
        #
        
        self._notificationsSent += 1;
        addTime = datetime.datetime.now() + datetime.timedelta(seconds=self._secondsLeft);
        addTimeFormatted = "%02d:%02d:%02d on %02d-%02d-%02d" % (addTime.hour, addTime.minute, addTime.second, addTime.year, addTime.month, addTime.day);
        minutesLeft = int(self._secondsLeft / 60);
        secondsLeftmod = int(self._secondsLeft % 60);
        notificationMessage = "Subject: Brew Notification\n\nAt %s, %s. (about %s minutes and %s seconds from now)" % (addTimeFormatted, self._message, minutesLeft, secondsLeftmod);
        print ("Sending notification: %s" % notificationMessage);
        
        if BrewPreferences.areValid and BrewPreferences.notificationToAddresses:
            try:
                print ("Sending notification with SMTP.");
                sendSimpleMailAsync(
                    BrewPreferences.notificationSmtpServer,
                    BrewPreferences.notificationSmtpUsername, 
                    BrewPreferences.notificationSmtpPassword,
                    BrewPreferences.notificationFromAddress, 
                    BrewPreferences.notificationToAddresses, 
                    notificationMessage
                );
            #
            except Exception as ex:
                print (ex);
            #
        #
    #
#

class BrewScheduleException(Exception): 
    pass;
#

def parseTagAsFloat(xElement, subElementName):
    result = 0;
    resultString = xElement.find(subElementName).text;
    try:
        result = float(resultString);
    #
    except: 
        raise BrewScheduleException("Could not parse <%s> tag content: '%s'." % (subElementName, resultString));
    #
    return result;
#

class BrewSchedule:
    def unset(self):
        self.actionItems = [];
        self.xBrewBoilAdditions = ElementTree.Element("BrewBoilAdditions");
    #
    
    def __init__(self, _app):
        self.unset();
        self.app = _app;
        self.actionItemTitle = None;
        self.actionItemLabel = None;
        self.actionItemFrame = None;
        self.startSeconds = 0;
        self.updateTime = 0;
        self.clockSecondsMax = 0;
        self.clockIsPaused = True;
    #
    
    def __str__(self):
        return "".join(["\nAction Item #%02d:\n%s\n\n" % (idx, item) for (idx, item) in enumerate(self.actionItems, start=1)]);
    #
    
    def advanceClock(self):
        lastUpdateTime = self.updateTime;
        self.updateTime = time.time();
        if self.clockIsPaused:
            self.startSeconds += (self.updateTime - lastUpdateTime);
        #
    #
    
    def getTimeSecondsLeft(self):
        secondsElapsedSincedStart = self.updateTime - self.startSeconds;
        timeLeft = self.clockSecondsMax - secondsElapsedSincedStart;
        timeLeft = timeLeft if timeLeft >= 0 else 0;
        return timeLeft;
    #
    
    
    def start(self):
        if self.actionItemTitle: self.actionItemTitle.destroy();
        self.actionItemTitle = Label(self.app._actionItemFrameRoot, bg=self.app._actionItemFrameRoot["bg"], fg=CC.black, text="[Action Item Title]", font=CustomFonts.labelMedium, anchor=W, justify=LEFT);
        self.actionItemTitle.pack(side=TOP, fill=X, anchor=W);
        if self.actionItemLabel: self.actionItemLabel.destroy();
        self.actionItemLabel = Label(self.app._actionItemFrameRoot, bg=self.app._actionItemFrameRoot["bg"], fg=CC.black, text="[Action Item Label]", font=CustomFonts.monoMedium, anchor=W, justify=LEFT);
        self.actionItemLabel.pack(side=TOP, fill=X, anchor=W);
        self.currentItemIndex = -1;
        self.__advanceOneActionItem();
    #
    
    def __advanceOneActionItem(self):
        self.currentItemIndex += 1;
        self.runActionItemSetup = True;
        self.endCurrentActionItem = False;
        if self.actionItemFrame: self.actionItemFrame.destroy();
        self.actionItemFrame = Frame(self.app._actionItemFrameRoot, bg=CC.gray_main);
        self.actionItemFrame.pack(side=TOP, expand=True, fill=BOTH);
        self.__execute();
    #
    
    def __execute(self):
        # Only keep executing if current index is valid
        if self.currentItemIndex >= len(self.actionItems):
            self.startSeconds = 0;
            self.updateTime = 0;
            self.clockSecondsMax = 0;
            self.clockIsPaused = True;
            self.actionItemTitle.config(text="Brew Finished");
            self.actionItemLabel.config(text="Brew Finished");
            print ("Reached end of brew schedule.");
            return;
        #
        
        # Move to next item if current flag is set
        if self.endCurrentActionItem:
            self.__advanceOneActionItem();
            return;
        #
        
        currentActionItem = self.actionItems[self.currentItemIndex];
        
        # Run clock setup and start event if flag is set, otherwise run executing event
        if self.runActionItemSetup:
            self.runActionItemSetup = False;
            self.startSeconds = time.time();
            self.updateTime = self.startSeconds;
            self.clockSecondsMax = currentActionItem.durationSeconds;
            self.clockIsPaused = True;
            self.actionItemTitle.config(text=currentActionItem.title);
            self.actionItemLabel.config(text=currentActionItem.message);
            currentActionItem.onActionStart();
        #
        else:
            # TODO: check reflected brew step to see if it matches
            currentActionItem.onActionExecuting(self.app._currentRO);
        #
        
        # Advance clock time
        self.advanceClock();
        
        # Queue write data (sent every iteration, unless executing event has set the end-flag to true)
        if not self.endCurrentActionItem:
            self.app._brewIO.writeOne(currentActionItem.writeObject);
        #
        
        # Run again after refresh period
        self.app.after(self.app._brewIO.refreshMillis, self.__execute);
    #
    
    
    def setRecipe(self, xRecipe):
        self.unset();
        
        
        ##################
        ### Brew Setup ###
        ##################
        
        ## Remind brewer to clean equipment ##
        _preClean = BrewActionItem(BrewStep.ST_READY);
        _preClean.title = "Manual Brewery Pre-clean";
        _preClean.message = "Please ensure that the brewery is clean. \nPress the 'Brewery Cleaned' button to continue.";
        def _preClean_onActionStart():
            def preCleanedCommand(): self.endCurrentActionItem = True;
            preCleanedButton = Button(self.actionItemFrame, command=preCleanedCommand, bd=5, relief=RAISED, bg=CC.purple, fg=CC.white, text="Brewery Cleaned", font=CustomFonts.button);
            preCleanedButton.pack(side=TOP, anchor=W);
        #
        _preClean.onActionStart = _preClean_onActionStart;
        self.actionItems.append(_preClean);
        
        ## Add grain to MLT ##
        _addGrain = BrewActionItem(BrewStep.ST_READY);
        _addGrain.title = "Brew Setup";
        _addGrain.message = "Please add grain to the MLT. \nPress the 'Added Grain' button to continue.";
        def _addGrain_onActionStart():
            def addedGrainCommand(): self.endCurrentActionItem = True;
            addedGrainButton = Button(self.actionItemFrame, command=addedGrainCommand, bd=5, relief=RAISED, bg=CC.olive, fg=CC.white, text="Added Grain", font=CustomFonts.button);
            addedGrainButton.pack(side=TOP, anchor=W);
        #
        _addGrain.onActionStart = _addGrain_onActionStart;
        self.actionItems.append(_addGrain);
        
        
        ##############
        ### Strike ###
        ##############
        
        # parse infusion step info
        xMashSteps = xRecipe.findall("MASH/MASH_STEPS/MASH_STEP");
        if 0 == len(xMashSteps):
            raise BrewScheduleException("No mash steps found.");
        #
        xInfusionStep = xMashSteps[0];
        if "Infusion" != xInfusionStep.find("TYPE").text:
            raise BrewScheduleException("First mash step is not an infusion step.");
        #
        infuse_amount_L = parseTagAsFloat(xInfusionStep, "INFUSE_AMOUNT");
        
        infuse_temp_F = 0;
        infuse_temp_value = 0;
        infuse_temp_str = xInfusionStep.find("INFUSE_TEMP").text.upper();
        infuse_temp_str_parts = infuse_temp_str.split(" ");
        try:
            infuse_temp_value = float(infuse_temp_str_parts[0]);
        #
        except:
            raise BrewScheduleException("Could not parse <INFUSE_TEMP> tag content: '" + infuse_temp_str + "'.");
        #
        if "F" == infuse_temp_str_parts[1]: infuse_temp_F = infuse_temp_value; 
        elif "C" == infuse_temp_str_parts[1]: infuse_temp_F = convertCtoF(infuse_temp_value);
        else: raise BrewScheduleException("Unexpected <INFUSE_TEMP> tag temperature unit: '" + infuse_temp_str + "'.");
        
        ## Add water to HLT ##
        _fillHlt = BrewActionItem(BrewStep.ST_FILL);
        _fillHlt.title = "Strike Preparation";
        _fillHlt.message = "Filling the HLT.";
        def _fillHlt_onActionExecuting(ro):
            if ro.levelHlt >= 1.0: self.endCurrentActionItem = True;
        #
        _fillHlt.onActionExecuting = _fillHlt_onActionExecuting;
        self.actionItems.append(_fillHlt);
        
        ## Heat HLT to Strike/Infusion temp ##
        _heatHlt = BrewActionItem(BrewStep.ST_STRIKE, tsp=infuse_temp_F);
        _heatHlt.title = "Strike Preparation";
        _heatHlt.message = "Heating the HLT to %.1f F" % infuse_temp_F;
        def _heatHlt_onActionExecuting(ro):
            if ro.tempHlt >= infuse_temp_F: self.endCurrentActionItem = True;
        #
        _heatHlt.onActionExecuting = _heatHlt_onActionExecuting;
        self.actionItems.append(_heatHlt);
        
        ## Transfer strike water from HLT to MLT ##
        _transferStrike = BrewActionItem(BrewStep.ST_MASH_IN, amt=infuse_amount_L);
        _transferStrike.title = "Strike";
        _transferStrike.message = "Transferring strike water to MLT.";
        def _transferStrike_onActionExecuting(ro):
            if ro.levelMlt >= 1.0: self.endCurrentActionItem = True;
        #
        _transferStrike.onActionExecuting = _transferStrike_onActionExecuting;
        self.actionItems.append(_transferStrike);
        
        ## Re-fill HLT for heat exchange ##
        _refillHlt = BrewActionItem(BrewStep.ST_FILL);
        _refillHlt.title = "Mash Preparation";
        _refillHlt.message = "Refilling HLT for heat exchange.";
        def _refillHlt_onActionExecuting(ro):
            if ro.levelHlt >= 1.0: self.endCurrentActionItem = True;
        #
        _refillHlt.onActionExecuting = _refillHlt_onActionExecuting;
        self.actionItems.append(_refillHlt);
        
        
        ##################
        ### Mash Steps ###
        ##################
        
        xPreSpargeStep = ElementTree.Element("MASH_STEP");
        ElementTree.SubElement(xPreSpargeStep, "NAME").text = "Pre-Sparge";
        ElementTree.SubElement(xPreSpargeStep, "STEP_TIME").text = "0.1";
        ElementTree.SubElement(xPreSpargeStep, "STEP_TEMP").text = str(convertFtoC(168.0));
        xMashSteps.append(xPreSpargeStep);
        
        mashStepNumber = 0;
        for xMashStep in xMashSteps:
            
            mashStepNumber += 1;
            
            # parse mash step info
            step_name = xMashStep.find("NAME").text;
            step_time_min = parseTagAsFloat(xMashStep, "STEP_TIME");
            step_time_sec = step_time_min * 60;
            step_temp_C = parseTagAsFloat(xMashStep, "STEP_TEMP");
            step_temp_F = convertCtoF(step_temp_C);
            
            ## Steep/Mash at temp ##
            _mash = BrewActionItem(BrewStep.ST_MASH, durationSeconds=step_time_sec, tsp=step_temp_F);
            _mash.title = "Mash Step #%s: %s" % (mashStepNumber, step_name);
            _mash.message = "Holding MLT at %.1f F for %.2f minutes." % (step_temp_F, step_time_min);
            # need this closure-ish madness due to loop variable reuse
            def _mash_Events(step_temp_F=step_temp_F, _mash=_mash):
                def _mash_onActionStart():
                    _mash.warningLabel = Label(self.actionItemFrame, bg=self.actionItemFrame["bg"], fg=CC.red, text="", font=CustomFonts.monoLargeBold, anchor=W, justify=LEFT);
                    _mash.warningLabel.pack(side=TOP, fill=X, anchor=W);
                    self.clockIsPaused = False;
                #
                def _mash_onActionExecuting(ro):
                    if self.getTimeSecondsLeft() <= 0: 
                        self.endCurrentActionItem = True;
                        return;
                    #
                    self.clockIsPaused = not isWithinTolerance(ro.tempMlt, step_temp_F, MASH_TEMP_TOLERANCE_UP, MASH_TEMP_TOLERANCE_DOWN);
                    if ro.tempMlt > step_temp_F:
                        _mash.warningLabel.config(text="ADD ICE: MLT IS AT %.1f F" % ro.tempMlt);
                        # TODO: ring warning bell
                    #
                    else:
                        _mash.warningLabel.config(text="");
                        # TODO: stop ringing warning bell
                    #
                #
                return (_mash_onActionStart, _mash_onActionExecuting);
            #
            _mash.onActionStart, _mash.onActionExecuting = _mash_Events();
            self.actionItems.append(_mash);
            
        #
        
        
        #######################
        ### Sparge and Boil ###
        #######################
        
        # parse boil info
        boil_size_L = parseTagAsFloat(xRecipe, "BOIL_SIZE");
        boil_time_min = parseTagAsFloat(xRecipe, "BOIL_TIME");
        boil_time_sec = boil_time_min * 60;
        
        # get boil addition sub-schedule
        brew_boil_additions = [];
        xBoilMiscs = [xe for xe in xRecipe.findall("MISCS/MISC") if xe.find("USE").text == "Boil"];
        xHops = xRecipe.findall("HOPS/HOP");
        xBoilHops = [xe for xe in xHops if xe.find("USE").text == "Boil"];
        xAromaHops = [xe for xe in xHops if xe.find("USE").text == "Aroma"];
        xBoilAdditions = xBoilMiscs + xBoilHops + xAromaHops;
        xBoilAdditions.sort(key=lambda xe: -float(xe.find("TIME").text));
        
        for xBoilAddition in xBoilAdditions:
            type = xBoilAddition.tag[0].upper() + xBoilAddition.tag[1:].lower();
            name = xBoilAddition.find("NAME").text;
            use = xBoilAddition.find("USE").text;
            time_ = parseTagAsFloat(xBoilAddition, "TIME");
            amount = parseTagAsFloat(xBoilAddition, "AMOUNT");
            amountType = AmountType.kilogram;
            if xBoilAddition.tag == "MISC":
                amountIsWeight = xBoilAddition.find("AMOUNT_IS_WEIGHT").text.upper() == "TRUE";
                if not amountIsWeight: 
                    amountIsItem = " item" in xBoilAddition.find("DISPLAY_AMOUNT").text.lower();
                    amountType = AmountType.item if amountIsItem else AmountType.liter;
                #
            #
            bba = BrewBoilAddition(type, name, use, time_, amount, amountType);
            brew_boil_additions.append(bba);
            self.xBrewBoilAdditions.append(bba.xElement);
            print (bba);
        #
        print ("");
        self.app._scheduleData.bind(self.xBrewBoilAdditions);
        self.app._scheduleBoilTimeText.config(text="%.2f minutes" % boil_time_min);
        first_wort_hops = [bba for bba in brew_boil_additions if bba.use == "First Wort"];
        regular_boil_additions = [bba for bba in brew_boil_additions if bba.use == "Boil"];
        flameout_hops = [bba for bba in brew_boil_additions if bba.use == "Aroma"];
        
        ## Sparge / Lauter ##
        _sparge = BrewActionItem(BrewStep.ST_SPARGE, amt=boil_size_L);
        _sparge.title = "Fly Sparge";
        _sparge.message = "Sparge / lauter until BK reaches %.1f L." % boil_size_L;
        def _sparge_onActionStart():
            self.app._setNotificationFrameRootShown(True);
            for fwh in first_wort_hops:
                notificationFrame = NotificationFrame(self.app._notificationContainer, fwh.notificationMessage, 0);
                notificationFrame.show();
            #
        #
        def _sparge_onActionExecuting(ro):
            if ro.levelBk >= 1.0: self.endCurrentActionItem = True;
        #
        _sparge.onActionStart = _sparge_onActionStart;
        _sparge.onActionExecuting = _sparge_onActionExecuting;
        self.actionItems.append(_sparge);
        
        ## Boil ##
        _boil = BrewActionItem(BrewStep.ST_BOIL, durationSeconds=boil_time_sec);
        _boil.title = "Boil";
        _boil.message = "Holding BK at a rolling boil for %.2f minutes." % boil_time_min;
        def _boil_onActionStart():
            # _boil.currentNotification = Label(self.actionItemFrame, bg=self.actionItemFrame["bg"], fg=CC.blue, text="", font=CustomFonts.monoLargeBold, anchor=W, justify=LEFT);
            # _boil.currentNotification.pack(side=TOP, fill=X, anchor=W);
            self.clockIsPaused = False;
            _boil.updateTime = time.time();
            _boil.notificationFrames = [];
            for rba in regular_boil_additions:
                notificationSecondsMax = (rba.time * 60);
                notificationFrame = NotificationFrame(self.app._notificationContainer, rba.notificationMessage, notificationSecondsMax);
                notificationFrame.show();
                notificationFrame.setTimeLeftOnBoil(boil_time_sec);
                _boil.notificationFrames.append(notificationFrame);
            #
        #
        def _boil_onActionExecuting(ro):
            if self.getTimeSecondsLeft() <= 0: 
                self.endCurrentActionItem = True;
                return;
            #
            self.clockIsPaused = ro.tempBk < 208.0; # TODO: and not ro.hasRollingBoil
            
            timeSecondsLeft = self.getTimeSecondsLeft();
            if not self.clockIsPaused:
                for frame in _boil.notificationFrames:
                    frame.setTimeLeftOnBoil(timeSecondsLeft);
                #
            #
            
            ## TODO: any warnings??
        #
        
        _boil.onActionStart = _boil_onActionStart;
        _boil.onActionExecuting = _boil_onActionExecuting;
        self.actionItems.append(_boil);
        
        
        # parse whirlpool info
        whirl_time_min = 0;
        for bba in brew_boil_additions:
            if bba.use == "Aroma" and bba.time > whirl_time_min: 
                whirl_time_min = bba.time;
            #
        #
        if not whirl_time_min: whirl_time_min = 10;
        whirl_time_sec = whirl_time_min * 60;
        
        ## Whirlpool ##
        _whirlpool = BrewActionItem(BrewStep.ST_STEEP, durationSeconds=whirl_time_sec);
        _whirlpool.title = "Whirlpool";
        _whirlpool.message = "Whirlpooling for %.2f minutes. \nManually change whirl time with commands below." % whirl_time_min;
        def _whirlpool_onActionStart():
            whirlpoolControlFrame = Frame(self.actionItemFrame, bg=self.actionItemFrame["bg"]);
            whirlpoolControlFrame.pack(side=TOP, fill=X);
            def endWhirlpool(): self.endCurrentActionItem = True;
            endWhirlpoolButton = Button(whirlpoolControlFrame, command=endWhirlpool, bd=5, relief=RAISED, bg=CC.teal, fg=CC.navy, text="End Immediately", font=CustomFonts.button);
            endWhirlpoolButton.pack(side=LEFT, anchor=W, padx=5);
            def addTimeWhirlpool(dt): 
                self.clockSecondsMax += dt;
            #
            subtractMinuteWhirlpoolButton = Button(whirlpoolControlFrame, command=lambda: addTimeWhirlpool(-60), bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="- 1 min", font=CustomFonts.button);
            subtractMinuteWhirlpoolButton.pack(side=LEFT, anchor=W, padx=5);
            addMinuteWhirlpoolButton = Button(whirlpoolControlFrame, command=lambda: addTimeWhirlpool(60), bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="+ 1 min", font=CustomFonts.button);
            addMinuteWhirlpoolButton.pack(side=LEFT, anchor=W, padx=5);
            self.clockIsPaused = False;
        #
        def _whirlpool_onActionExecuting(ro):
            if self.getTimeSecondsLeft() <= 0: 
                self.endCurrentActionItem = True;
                return;
            #
        #
        _whirlpool.onActionStart = _whirlpool_onActionStart;
        _whirlpool.onActionExecuting = _whirlpool_onActionExecuting;
        self.actionItems.append(_whirlpool);
        
        
        ## Hold whirlpool to confirm fermentor presence ##
        _postWhirlpool = BrewActionItem(BrewStep.ST_STEEP);
        _postWhirlpool.title = "Whirlpool Complete";
        _postWhirlpool.message = "Jim, is the fermenter cleaned and present?";
        def _postWhirlpool_onActionStart():
            def gotFermentor(): self.endCurrentActionItem = True;
            gotFermentorButton = Button(self.actionItemFrame, command=gotFermentor, bd=5, relief=RAISED, bg=CC.olive, fg=CC.white, text="Yes, the fermenter is present.", font=CustomFonts.button);
            gotFermentorButton.pack(side=TOP, anchor=W);
        #
        _postWhirlpool.onActionStart = _postWhirlpool_onActionStart;
        self.actionItems.append(_postWhirlpool);
        
        
        ###################
        ### Finish Brew ###
        ###################
        
        ## Transfer out to fermentor ##
        _fillFermentor = BrewActionItem(BrewStep.ST_FILLFERM);
        _fillFermentor.title = "Fill Fermentor";
        _fillFermentor.message = "Transferring from BK to fermentor. \nPress the 'End Immediately' button to stop early.";
        def _fillFermentor_onActionStart():
            self.app._setNotificationFrameRootShown(False);
            def endFillFermentor(): 
                self.endCurrentActionItem = tkMessageBox.askyesno("End Immediately", "Are you sure you want to stop filling the fermentor?", default=tkMessageBox.NO);
            #
            endFillFermentorButton = Button(self.actionItemFrame, command=endFillFermentor, bd=5, relief=RAISED, bg=CC.orange, fg=CC.black, text="End Immediately", font=CustomFonts.button);
            endFillFermentorButton.pack(side=TOP, anchor=W);
        #
        def _fillFermentor_onActionExecuting(ro):
            if ro.levelBk <= 0: self.endCurrentActionItem = True;
        #
        _fillFermentor.onActionStart = _fillFermentor_onActionStart;
        _fillFermentor.onActionExecuting = _fillFermentor_onActionExecuting;
        self.actionItems.append(_fillFermentor);
        
        ## Post-brew / Pre-Clean-in-Place ##
        _postBrew = BrewActionItem(BrewStep.ST_READY);
        _postBrew.title = "Clean-in-Place";
        _postBrew.message = "The brewery will now perform a clean-in-place. \nPress the 'Start CIP' button to continue.";
        def _postBrew_onActionStart():
            def startCipCommand(): self.endCurrentActionItem = True;
            startCipButton = Button(self.actionItemFrame, command=startCipCommand, bd=5, relief=RAISED, bg=CC.fuchsia, fg=CC.white, text="Start CIP", font=CustomFonts.button);
            startCipButton.pack(side=TOP, anchor=W);
        #
        _postBrew.onActionStart = _postBrew_onActionStart;
        self.actionItems.append(_postBrew);
        
        ## Clean-in-Place ##
        _cleanInPlace = BrewActionItem(BrewStep.ST_CIP);
        _cleanInPlace.title = "Clean-in-Place";
        _cleanInPlace.message = "In progress.";
        def _cleanInPlace_onActionExecuting(ro):
            if BrewStep.ST_DONE == ro.brewStep: self.endCurrentActionItem = True;
        #
        _cleanInPlace.onActionExecuting = _cleanInPlace_onActionExecuting;
        self.actionItems.append(_cleanInPlace);
        
        
        ## Done ##
        _done = BrewActionItem(BrewStep.ST_DONE);
        _done.title = "Brew Done";
        _done.message = "Brew Done";
        def _done_onActionExecuting(ro):
            self.endCurrentActionItem = True;
        #
        _done.onActionExecuting = _done_onActionExecuting;
        self.actionItems.append(_done);
    #
#


class Page(Enum):
    none = 0;
    recipe = 1;
    schedule = 2;
    system = 3;
#

class MenuButton(Button):
    allButtons = [];
    pageSelectionEvent = CustomEvent();
    def __init__(self, _parent, _page, bg, fg, text):
        Button.__init__(
            self,
            _parent, 
            command=lambda: MenuButton.pageSelectionEvent.publish(_page),
            bd=5, relief=RAISED,
            bg=bg, fg=fg, 
            text=text, font=CustomFonts.button
        );
        self.page = _page;
        MenuButton.allButtons.append(self);
    #
#

def showHideButtons(argPage):
    for button in MenuButton.allButtons:
        button.config(relief=(SUNKEN if (button.page == argPage) else RAISED));
    #
#
MenuButton.pageSelectionEvent.subscribe(showHideButtons);

class ScreenFrame(Frame):
    allFrames = [];
    def __init__(self, _parent, _page):
        Frame.__init__(self, _parent, bg=CC.gray_main);
        self.page = _page;
        ScreenFrame.allFrames.append(self);
    #
#

def showHideScreens(argPage):
    for frame in ScreenFrame.allFrames:
        frame.pack_forget();
    #
    for frame in ScreenFrame.allFrames:
        if frame.page == argPage:
            frame.pack(side=LEFT, fill=BOTH, expand=True);
            break;
        #
    #
#
MenuButton.pageSelectionEvent.subscribe(showHideScreens);



class BrewInterface(Tk):
    def __init__(self): 
        Tk.__init__(self);
        
        self._currentRO = BrewReadObject(None);
        self._brewIO = BrewIO(PORT_ID, BAUD_RATE, REFRESH_RATE, USES_TEST_MODE, INPUT_NEWLINE_CHAR);
        self.__schedule = BrewSchedule(self);
        
        ################
        ## Root Frame ##
        ################
        
        self.__rootFrame = Frame(self);
        self.__rootFrame.pack(anchor=CENTER, fill=BOTH, expand=True);
        
        
        ##########
        ## Menu ##
        ##########
        
        self.__menuFrame = Frame(self.__rootFrame, bg=CC.gray_menu);
        self.__menuFrame.pack(side=TOP, fill=X, ipadx=6);
        
        self.__menuBottomBorder = Frame(self.__menuFrame, bg="black", height=1);
        self.__menuBottomBorder.pack(side=BOTTOM, fill=X);
        
        self.__titleLabel = Label(self.__menuFrame, padx=20, bg=CC.gray_menu, fg="black", text=APP_TITLE, font=CustomFonts.title);
        self.__titleLabel.pack(side=LEFT);
        
        # # self.__subtitleLabel = Label(self.__menuFrame, bg=CC.gray_menu, fg="black", text="SUBTITLE", font=CustomFonts.title);
        # # self.__subtitleLabel.pack(side=BOTTOM);
        
        self.__recipeButton = MenuButton(self.__menuFrame, Page.recipe, bg=CC.maroon, fg=CC.orange, text="Recipe");
        self.__recipeButton.pack(side=LEFT, fill=Y, padx=5, pady=5);
        
        self.__systemButton = MenuButton(self.__menuFrame, Page.system, bg=CC.olive, fg=CC.lime, text="System");
        self.__systemButton.pack(side=LEFT, fill=Y, padx=5, pady=5);
        
        self.__scheduleButton = MenuButton(self.__menuFrame, Page.schedule, bg=CC.blue, fg=CC.aqua, text="Boil Schedule");
        self.__scheduleButton.pack(side=LEFT, fill=Y, padx=5, pady=5);
        
        def closeButtonAction():
            if tkMessageBox.askyesno("Close", "Are you sure you want to close the interface and halt brewing?", default=tkMessageBox.NO):
                self._brewIO.setCloseOnNextTick();
                self.destroy();
            #
        #
        self.__closeButton = Button(self.__menuFrame, command=closeButtonAction, bd=5, relief=RAISED, bg=CC.black, fg=CC.white, text="Close", font=CustomFonts.button);
        self.__closeButton.pack(side=RIGHT, fill=Y, padx=5, pady=5);
        
        
        ###################
        ## Recipe Screen ##
        ###################
        
        self.__recipeFrame = ScreenFrame(self.__rootFrame, Page.recipe);
        self.__recipeFrame.grid_rowconfigure(2, weight=1);
        self.__recipeFrame.grid_columnconfigure(2, weight=1)
        
        def chooseRecipe():
            self.__errorLabel.config(text="");
            self.__startScheduleButton.config(state=DISABLED, relief=FLAT, bg=CC.black);
            try:
                fname = tkFileDialog.askopenfilename(defaultextension=".xml");
                self.__filenameLabel.config(text=fname.split("/")[-1]);
                if not os.path.isfile(fname):
                    self.__errorLabel.config(text="No file chosen");
                    self.__recipeData.bind(ElementTree.Element("__Empty__"));
                    return;
                #
                xtree = ElementTree.parse(fname);
                xroot = xtree.getroot();
                
                xrecipe = xroot.find(".//RECIPE");
                self.__recipeData.bind(xrecipe);
                self.__schedule.setRecipe(xrecipe);
                self.__startScheduleButton.config(state=NORMAL, relief=RAISED, bg=CC.red);
                ###print (self.__schedule);
            #
            except Exception as ex:
                self.__errorLabel.config(text="Error parsing file");
                self.__recipeData.bind(ElementTree.Element("__Empty__"));
                raise ex;
            #
        #
        
        self.__chooseRecipeButton = Button(self.__recipeFrame, command=chooseRecipe, bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="Choose File", font=CustomFonts.button);
        self.__chooseRecipeButton.grid(row=0, column=1, sticky=W, padx=2, pady=2);
        
        self.__filenameLabel = Label(self.__recipeFrame, bg=self.__recipeFrame["bg"], fg=CC.black, font=CustomFonts.monoMediumBold);
        self.__filenameLabel.grid(row=0, column=2, sticky=W, padx=2, pady=2);
        
        self.__errorLabel = Label(self.__recipeFrame, bg=self.__recipeFrame["bg"], fg=CC.red, font=CustomFonts.text);
        self.__errorLabel.grid(row=0, column=3, columnspan=2, sticky=E, padx=2, pady=2);
        
        def startSchedule():
            self.__schedule.start();
            MenuButton.pageSelectionEvent.publish(Page.system);
            self.__chooseRecipeButton.config(state=DISABLED, relief=FLAT, bg=CC.black, fg=CC.white, text="File Chosen");
            self.__startScheduleButton.config(state=DISABLED, relief=FLAT, bg=CC.black, text="Brew Started");
        #
        self.__startScheduleButton = Button(self.__recipeFrame, command=startSchedule, bd=5, relief=FLAT, bg=CC.black, fg=CC.white, text="Start Brew", font=CustomFonts.button, state=DISABLED);
        self.__startScheduleButton.grid(row=1, column=1, sticky=W, padx=2, pady=2);
        
        self.__recipeDataContainer = VerticalScrolledFrame(self.__recipeFrame, bg=self.__recipeFrame["bg"]);
        self.__recipeDataContainer.grid(row=2, column=1, rowspan=2, columnspan=3, sticky=(N,S,E,W), padx=2, pady=2);
        self.__recipeDataContainer.interior.config(bg=self.__recipeFrame["bg"]);
        
        recipe_scroll = lambda up: self.__recipeDataContainer.canvas.yview_scroll((-1 if up else 1) * 2, "units");
        recipe_moveto = lambda top: self.__recipeDataContainer.canvas.yview_moveto(0 if top else 1);
        
        self.__scrollRecipeUpFrame = Frame(self.__recipeFrame, bg=self.__recipeFrame["bg"]);
        self.__scrollRecipeUpFrame.grid(row=2, column=4, sticky=(W,E,N), padx=2, pady=2);
        
        self.__scrollRecipeTopButton = Button(self.__scrollRecipeUpFrame, command=lambda: recipe_moveto(True), bd=5, relief=RAISED, bg=CC.navy, fg=CC.white, text="Top", font=CustomFonts.button);
        self.__scrollRecipeTopButton.pack(side=TOP, fill=X);
        
        self.__scrollRecipeUpButton = Button(self.__scrollRecipeUpFrame, command=lambda: recipe_scroll(True), bd=5, relief=RAISED, bg=CC.blue, fg=CC.white, text="Up", font=CustomFonts.button);
        self.__scrollRecipeUpButton.pack(side=TOP, fill=X);
        
        self.__scrollRecipeDownFrame = Frame(self.__recipeFrame, bg=self.__recipeFrame["bg"]);
        self.__scrollRecipeDownFrame.grid(row=3, column=4, sticky=(W,E,S), padx=2, pady=2);
        
        self.__scrollRecipeBottomButton = Button(self.__scrollRecipeDownFrame, command=lambda: recipe_moveto(False), bd=5, relief=RAISED, bg=CC.navy, fg=CC.white, text="Bottom", font=CustomFonts.button);
        self.__scrollRecipeBottomButton.pack(side=BOTTOM, fill=X);
        
        self.__scrollRecipeDownButton = Button(self.__scrollRecipeDownFrame, command=lambda: recipe_scroll(False), bd=5, relief=RAISED, bg=CC.blue, fg=CC.white, text="Down", font=CustomFonts.button);
        self.__scrollRecipeDownButton.pack(side=BOTTOM, fill=X);
        
        DataSettings.scaling = 1.2;
        self.__recipeData = DataFrame("", [
            DataHeader("h2", "Recipe"),
            DataFrame("", [
                DataLabel("Name:"), DataValue("NAME"), 
                DataLabel("Type:"), DataValue("TYPE"),
                DataLabel("Brewer:"), DataValue("BREWER"),
                DataLabel("Assistant Brewer:"), DataValue("ASST_BREWER"),
            ]),
            DataFrame("", [
                DataLabel("Calories:"), DataValue("CALORIES"),
                DataLabel("Est. ABV:"), DataValue("EST_ABV"),
                DataLabel("Taste Rating:"), DataValue("TASTE_RATING", "float-1"),
            ]),
            DataHeader("h2", "Style"),
            DataFrame("STYLE", [
                DataLabel("Name:"), DataValue("NAME"), 
                DataLabel("Category:"), DataValue("CATEGORY"),
            ]),
            DataHeader("h2", "Waters"),
            DataFrame("", [
                DataTable("WATERS", "WATER", CC.gray_menu, [
                    DataTableColumn("Name", "NAME"),
                    DataTableColumn("Amount", "AMOUNT"),
                    DataTableColumn("Ca^2+", "CALCIUM", "ppm", E),
                    DataTableColumn("Mg^2+", "MAGNESIUM", "ppm", E),
                    DataTableColumn("Na^1-", "SODIUM", "ppm", E),
                    DataTableColumn("HCO_3^1-", "BICARBONATE", "ppm", E),
                    DataTableColumn("Cl^1-", "CHLORIDE", "ppm", E),
                    DataTableColumn("SO_4^2-", "SULFATE", "ppm", E),
                ]),
            ]),
            DataHeader("h2", "Mash"),
            DataHeader("h3", "Non-Fermentable Additions"),
            DataFrame("", [
                DataTable("MISCS", "MISC", CC.gray_menu, [
                    DataTableColumn("Name", "NAME"),
                    DataTableColumn("Type", "TYPE"),
                    DataTableColumn("Use", "USE"),
                    DataTableColumn("Time", "TIME", "min", E),
                    DataTableColumn("Used For", "USE_FOR"),
                    DataTableColumn("Amount", "DISPLAY_AMOUNT", "string", E),
                ], DataTableRowFilter("USE", "eq", "Mash")),
            ]),
            DataHeader("h3", "Fermentables"),
            DataFrame("", [
                DataTable("FERMENTABLES", "FERMENTABLE", CC.gray_menu, [
                    DataTableColumn("Name", "NAME"),
                    DataTableColumn("Type", "TYPE"),
                    DataTableColumn("Amount", "AMOUNT", "lb-from-kg", E),
                    DataTableColumn("Yield", "YIELD", "percent-2", E),
                    DataTableColumn("Color", "COLOR", "float-2", E),
                ]),
            ]),
            DataHeader("h3", "Mash Profile"),
            DataFrame("MASH", [
                DataFrame("", [
                    DataLabel("Name:"), DataValue("NAME"), 
                ]),
                DataFrame("", [
                    DataLabel("Initial Grain Temp:"), DataValue("GRAIN_TEMP", "F-from-C"), 
                    DataLabel("Initial Mash Tun Temp:"), DataValue("TUN_TEMP", "F-from-C"), 
                ]),
                DataFrame("", [
                    DataLabel("Mash pH:"), DataValue("PH", "pH"), 
                    DataLabel("Sparge Temp:"), DataValue("SPARGE_TEMP", "F-from-C"), 
                ]),
            ], 0),
            DataHeader("h4", "Mash Steps"),
            DataFrame("MASH", [
                DataTable("MASH_STEPS", "MASH_STEP", CC.gray_menu, [
                    DataTableColumn("Name", "NAME"),
                    DataTableColumn("Type", "TYPE"),
                    DataTableColumn("Ramp Time", "RAMP_TIME", "min", E),
                    DataTableColumn("Step Time", "STEP_TIME", "min", E),
                    DataTableColumn("Step Temp", "STEP_TEMP", "F-from-C", E),
                    DataTableColumn("Description", "DESCRIPTION"),
                ]),
            ]),
            DataHeader("h2", "Boil"),
            DataFrame("EQUIPMENT", [
                DataLabel("Boil Size:"), DataValue("BOIL_SIZE", "gal-from-L"), 
                DataLabel("Boil Time:"), DataValue("BOIL_TIME", "min"),
            ]),
            DataHeader("h3", "Non-Hop Additions"),
            DataFrame("", [
                DataTable("MISCS", "MISC", CC.gray_menu, [
                    DataTableColumn("Name", "NAME"),
                    DataTableColumn("Type", "TYPE"),
                    DataTableColumn("Use", "USE"),
                    DataTableColumn("Time", "TIME", "min", E),
                    DataTableColumn("Used For", "USE_FOR"),
                    DataTableColumn("Amount", "DISPLAY_AMOUNT", "string", E),
                ], DataTableRowFilter("USE", "eq", "Boil")),
            ]),
            DataHeader("h3", "Hops"),
            DataFrame("", [
                DataTable("HOPS", "HOP", CC.gray_menu, [
                    DataTableColumn("Name", "NAME"),
                    DataTableColumn("Amount", "AMOUNT", "oz-from-kg", E),
                    DataTableColumn("Use", "USE"),
                    DataTableColumn("Time", "TIME", "min", E),
                    DataTableColumn("Type", "TYPE"),
                    DataTableColumn("Form", "FORM"),
                    DataTableColumn("Alpha", "ALPHA", "percent-2", E),
                    DataTableColumn("Beta", "BETA", "percent-2", E),
                    DataTableColumn("Origin", "ORIGIN"),
                ]),
            ]),
            DataHeader("h2", "Fermentation"),
            DataHeader("h3", "Yeasts"),
            DataFrame("", [
                DataTable("YEASTS", "YEAST", CC.gray_menu, [
                    DataTableColumn("Name", "NAME"),
                    DataTableColumn("Type", "TYPE"),
                    DataTableColumn("Form", "FORM"),
                    DataTableColumn("Amount", "DISPLAY_AMOUNT", "string", E),
                    DataTableColumn("Min Temp", "MIN_TEMPERATURE", "F-from-C", E),
                    DataTableColumn("Max Temp", "MAX_TEMPERATURE", "F-from-C", E),
                    DataTableColumn("Flocculation", "FLOCCULATION"),
                ]),
            ]),
            DataHeader("h3", "Fermentation Stages"),
            DataFrame("", [
                DataLabel("Primary"), 
                DataLabel("Length:"), DataValue("PRIMARY_AGE", "days"),
                DataLabel("Temperature:"), DataValue("PRIMARY_TEMP", "C"),
            ]),
            DataFrame("", [
                DataLabel("Secondary"), 
                DataLabel("Length:"), DataValue("SECONDARY_AGE", "days"),
                DataLabel("Temperature:"), DataValue("SECONDARY_TEMP", "C"),
            ]),
            DataFrame("", [
                DataLabel("Tertiary"), 
                DataLabel("Length:"), DataValue("TERTIARY_AGE", "days"),
                DataLabel("Temperature:"), DataValue("TERTIARY_TEMP", "C"),
            ]),
            DataFrame("", [
                DataLabel("Bottling"), 
                DataLabel("Length:"), DataValue("AGE", "days"),
                DataLabel("Temperature:"), DataValue("TEMP", "C"),
            ]),
        ], 0);
        self.__recipeData.build(self.__recipeDataContainer.interior);
        
        
        ###################
        ## System Screen ##
        ###################
        
        self.__systemFrame = ScreenFrame(self.__rootFrame, Page.system);
        self.__systemFrame.grid_rowconfigure(5, weight=1);
        self.__systemFrame.grid_columnconfigure(2, weight=1);
        
        # time left
        self.__timeLeftFrame = Frame(self.__systemFrame, bg=CC.gray_main);
        self.__timeLeftFrame.grid(rowspan=5, row=0, column=0, sticky=(N,W), padx=5, pady=5);
        
        self.__clockCanvas = Canvas(self.__timeLeftFrame, bg=CC.gray_main, highlightthickness=0, width=164, height=164);
        self.__clockCanvas.pack(side=TOP, anchor=NW, padx=5, pady=5);
        self.__clockCanvas.xview_moveto(0);
        self.__clockCanvas.yview_moveto(0);
        
        self.__timePercentArc = self.__clockCanvas.create_arc(12, 12, 152, 152, style=ARC, fill="", outline=CC.olive, width=20, start=90, extent=215);
        self.__secondsArc = self.__clockCanvas.create_arc(32, 32, 132, 132, style=ARC, fill="", outline=CC.olive, width=10, start=90, extent=215);
        self.__timeLeftText = self.__clockCanvas.create_text(82, 82, text="time", font=CustomFonts.text);
        
        # time label and max value
        self.__timeLeftLabel = Label(self.__timeLeftFrame, bg=CC.gray_main, fg="black", text="Time Left", font=CustomFonts.label);
        self.__timeLeftLabel.pack(side=TOP, padx=5, pady=0);
        
        self.__timeMaxText = Label(self.__timeLeftFrame, bg=CC.gray_main, fg="black", text="", font=CustomFonts.text);
        self.__timeMaxText.pack(side=TOP, padx=5);
        
        # current step info frame
        self.__currentStepInfoFrame = Frame(self.__systemFrame, bg=CC.gray_main);
        self.__currentStepInfoFrame.grid(row=0, column=1, rowspan=5, columnspan=2, sticky=(N,W,S,E), padx=5, pady=5);
        
        # action item frame
        self._actionItemFrameRoot = Frame(self.__currentStepInfoFrame, bg=CC.gray_main);
        self._actionItemFrameRoot.pack(side=TOP, anchor=W, padx=5, pady=5);
        
        # notification container
        self.__notificationFrameRoot = Frame(self.__currentStepInfoFrame, bg=CC.gray_menu);
        self.__notificationFrameRootShown = False;
        def _setNotificationFrameRootShown(show):
            if self.__notificationFrameRootShown and not show:
                self.__notificationFrameRootShown = False;
                self.__notificationFrameRoot.pack_forget();
            #
            elif show and not self.__notificationFrameRootShown:
                self.__notificationFrameRootShown = True;
                self.__notificationFrameRoot.pack(side=TOP, fill=BOTH, expand=True, anchor=W, padx=2, pady=2);
            #
        #
        self._setNotificationFrameRootShown = _setNotificationFrameRootShown;
        self.__notificationFrameRoot.grid_rowconfigure(0, weight=1);
        self.__notificationFrameRoot.grid_columnconfigure(1, weight=1);
        
        self.__notificationLabel = Label(self.__notificationFrameRoot, bg=self.__notificationFrameRoot["bg"], fg="black", text="Notifications: ", font=CustomFonts.labelMedium);
        self.__notificationLabel.grid(row=0, column=0, sticky=(N,W), padx=2, pady=2);
        
        self.__notificationScrollFrame = VerticalScrolledFrame(self.__notificationFrameRoot, bg=self.__notificationFrameRoot["bg"]);
        self.__notificationScrollFrame.grid(row=0, column=1, sticky=(N,W,S,E), padx=2, pady=2);
        self.__notificationScrollFrame.canvas.config(width=0, height=0, bg=self.__notificationScrollFrame["bg"]);
        self._notificationContainer = self.__notificationScrollFrame.interior;
        self._notificationContainer.config(bg=self.__notificationScrollFrame["bg"]);
        self._notificationContainer.grid_columnconfigure(2, weight=1);
        
        self.__notificationScrollButtonFrame = Frame(self.__notificationFrameRoot, bg=self.__notificationScrollFrame["bg"]);
        self.__notificationScrollButtonFrame.grid(row=0, column=2, sticky=(N,W,S,E), padx=2, pady=2);
        
        notification_scroll = lambda up: self.__notificationScrollFrame.canvas.yview_scroll((-1 if up else 1) * 2, "units");
        
        self.__scrollNotificationUpButton = Button(self.__notificationScrollButtonFrame, command=lambda: notification_scroll(True), bd=2, relief=RAISED, bg=CC.blue, fg=CC.white, text="Up", font=CustomFonts.textSmall);
        self.__scrollNotificationUpButton.pack(side=TOP, fill=X, pady=(0,1));
        
        self.__scrollNotificationDownButton = Button(self.__notificationScrollButtonFrame, command=lambda: notification_scroll(False), bd=2, relief=RAISED, bg=CC.blue, fg=CC.white, text="Down", font=CustomFonts.textSmall);
        self.__scrollNotificationDownButton.pack(side=BOTTOM, fill=X, pady=(1,0));
        
        
        # tank frame
        self.__tankFrame = Frame(self.__systemFrame, bg=CC.gray_main);
        self.__tankFrame.grid(row=5, column=0, columnspan=3, sticky=S, padx=5, pady=5);
        self.__tankFrame.grid_rowconfigure(2, minsize=CONTAINER_HEIGHT);
        self.__tankFrame.grid_columnconfigure(0, weight=1);
        self.__tankFrame.grid_columnconfigure(1, weight=1);
        self.__tankFrame.grid_columnconfigure(2, weight=1);
        
        # tank labels
        self.__hltLabel = Label(self.__tankFrame, bg=CC.gray_main, fg=CC.black, text="HLT", font=CustomFonts.label);
        self.__hltLabel.grid(row=0, column=1, sticky=W, padx=5, pady=5);
        
        self.__mltLabel = Label(self.__tankFrame, bg=CC.gray_main, fg=CC.black, text="MLT", font=CustomFonts.label);
        self.__mltLabel.grid(row=0, column=3, sticky=W, padx=5, pady=5);
        
        self.__bkLabel = Label(self.__tankFrame, bg=CC.gray_main, fg=CC.black, text="BK", font=CustomFonts.label);
        self.__bkLabel.grid(row=0, column=5, sticky=W, padx=5, pady=5);
        
        # debug buttons for level and temp adjustment (12 total)
        if USES_TEST_MODE:
            for (n, id) in enumerate(["H", "M", "B"]):
                col = (2 * n + 1);
                prefix = "test" + id;
                debugTankFrame = Frame(self.__tankFrame, bg=self.__tankFrame["bg"]);
                debugTankFrame.grid(row=1, column=col, columnspan=2, sticky=W, padx=5, pady=5);
                for (name, suffix, qx) in [("Lvl", "lv", 0.05), ("Tmp", "pt", 3)]:
                    attrName = prefix + suffix;
                    for (sgn, sgnStr) in [(-1, "-"), (+1, "+")]:
                        buttonText = sgnStr + " " + name;
                        dx = sgn * qx;
                        def getUpdateFn(attrName=attrName, dx=dx):
                            def updateFn():
                                currentValue = getattr(self._brewIO, attrName);
                                setattr(self._brewIO, attrName, (currentValue + dx));
                            #
                            return updateFn;
                        #
                        fn = getUpdateFn();
                        debugTankButton = Button(debugTankFrame, command=fn, bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text=buttonText, font=CustomFonts.monoSmallBold);
                        debugTankButton.pack(side=LEFT, padx=2);
                    #
                #
            #
        #
        
        
        # tank containers
        self.__levelHltContainer = Frame(self.__tankFrame, bg=CC.gray_main, highlightthickness=1, highlightbackground="black");
        self.__levelHltContainer.grid(row=2, column=1, sticky=(N,S,E,W), padx=5, pady=(0,CONTAINER_MARGIN_BOTTOM));
        
        self.__tempHltContainer = Frame(self.__tankFrame, bg=CC.gray_main, highlightthickness=1, highlightbackground="black");
        self.__tempHltContainer.grid(row=2, column=2, sticky=(N,S,E,W), padx=(5,SPACING), pady=(0,CONTAINER_MARGIN_BOTTOM));
        
        self.__levelMltContainer = Frame(self.__tankFrame, bg=CC.gray_main, highlightthickness=1, highlightbackground="black");
        self.__levelMltContainer.grid(row=2, column=3, sticky=(N,S,E,W), padx=5, pady=(0,CONTAINER_MARGIN_BOTTOM));
        
        self.__tempMltContainer = Frame(self.__tankFrame, bg=CC.gray_main, highlightthickness=1, highlightbackground="black");
        self.__tempMltContainer.grid(row=2, column=4, sticky=(N,S,E,W), padx=(5,SPACING), pady=(0,CONTAINER_MARGIN_BOTTOM));
        
        self.__levelBkContainer = Frame(self.__tankFrame, bg=CC.gray_main, highlightthickness=1, highlightbackground="black");
        self.__levelBkContainer.grid(row=2, column=5, sticky=(N,S,E,W), padx=5, pady=(0,CONTAINER_MARGIN_BOTTOM));
        
        self.__tempBkContainer = Frame(self.__tankFrame, bg=CC.gray_main, highlightthickness=1, highlightbackground="black");
        self.__tempBkContainer.grid(row=2, column=6, sticky=(N,S,E,W), padx=5, pady=(0,CONTAINER_MARGIN_BOTTOM));
        
        # tank levels
        self.__levelHltBar = Frame(self.__levelHltContainer, bg=CC.blue, height=1, width=LEVEL_WIDTH);
        self.__levelHltBar.pack(side=BOTTOM, fill=X);
        
        self.__levelHltText = Label(self.__levelHltContainer, bg=CC.gray_menu, fg=CC.black, text="", font=CustomFonts.text);
        self.__levelHltText.pack(side=BOTTOM, anchor=E, pady=(0,CONTAINER_TEXT_SEPARATION));
        
        self.__levelMltBar = Frame(self.__levelMltContainer, bg=CC.blue, height=1, width=LEVEL_WIDTH);
        self.__levelMltBar.pack(side=BOTTOM, fill=X);
        
        self.__levelMltText = Label(self.__levelMltContainer, bg=CC.gray_menu, fg=CC.black, text="", font=CustomFonts.text);
        self.__levelMltText.pack(side=BOTTOM, anchor=E, pady=(0,CONTAINER_TEXT_SEPARATION));
        
        self.__levelBkBar = Frame(self.__levelBkContainer, bg=CC.blue, height=1, width=LEVEL_WIDTH);
        self.__levelBkBar.pack(side=BOTTOM, fill=X);
        
        self.__levelBkText = Label(self.__levelBkContainer, bg=CC.gray_menu, fg=CC.black, text="", font=CustomFonts.text);
        self.__levelBkText.pack(side=BOTTOM, anchor=E, pady=(0,CONTAINER_TEXT_SEPARATION));
        
        # tank temperatures
        self.__tempHltBar = Frame(self.__tempHltContainer, bg="black", height=1, width=TEMP_BAR_WIDTH);
        self.__tempHltBar.pack(side=BOTTOM, fill=X);
        
        self.__tempHltText = Label(self.__tempHltContainer, bg=CC.gray_menu, fg=CC.black, text="", font=CustomFonts.text);
        self.__tempHltText.pack(side=BOTTOM, anchor=E, pady=(0,CONTAINER_TEXT_SEPARATION));
        
        self.__tempMltBar = Frame(self.__tempMltContainer, bg="black", height=1, width=TEMP_BAR_WIDTH);
        self.__tempMltBar.pack(side=BOTTOM, fill=X);
        
        self.__tempMltText = Label(self.__tempMltContainer, bg=CC.gray_menu, fg=CC.black, text="", font=CustomFonts.text);
        self.__tempMltText.pack(side=BOTTOM, anchor=E, pady=(0,CONTAINER_TEXT_SEPARATION));
        
        self.__tempBkBar = Frame(self.__tempBkContainer, bg="black", height=1, width=TEMP_BAR_WIDTH);
        self.__tempBkBar.pack(side=BOTTOM, fill=X);
        
        self.__tempBkText = Label(self.__tempBkContainer, bg=CC.gray_menu, fg=CC.black, text="", font=CustomFonts.text);
        self.__tempBkText.pack(side=BOTTOM, anchor=E, pady=(0,CONTAINER_TEXT_SEPARATION));
        
        if USES_TEST_MODE:
            
            # debug buttons
            DEBUG_PADDING = 2;
            DEBUG_MARGIN = 2;
            DEBUG_FONT = CustomFonts.monoSmallBold;
            self.__debugButtonFrame = Frame(self.__systemFrame, bg=CC.gray_main);
            self.__debugButtonFrame.grid(rowspan=6, row=0, column=3, sticky=N, padx=2, pady=2);
            
            self.__debugLabel = Label(self.__debugButtonFrame, bg=CC.gray_main, fg=CC.black, text="Debug", font=CustomFonts.label);
            self.__debugLabel.pack(side=TOP, fill=X, padx=DEBUG_MARGIN, pady=DEBUG_MARGIN, ipadx=DEBUG_PADDING, ipady=DEBUG_PADDING);
            
            # def openIO():
                # self._brewIO.open();
            # #
            # self.__openIOButton = Button(self.__debugButtonFrame, command=openIO, bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="Open IO", font=DEBUG_FONT);
            # self.__openIOButton.pack(side=TOP, fill=X, padx=DEBUG_MARGIN, pady=DEBUG_MARGIN, ipadx=DEBUG_PADDING, ipady=DEBUG_PADDING);
            
            # def closeIO():
                # self._brewIO.setCloseOnNextTick();
            # #
            # self.__closeIOButton = Button(self.__debugButtonFrame, command=closeIO, bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="Close IO", font=DEBUG_FONT);
            # self.__closeIOButton.pack(side=TOP, fill=X, padx=DEBUG_MARGIN, pady=DEBUG_MARGIN, ipadx=DEBUG_PADDING, ipady=DEBUG_PADDING);
            
            # def debugSend():
                # ro = self._currentRO;
                # wo = BrewWriteObject(BrewStep(ro.brewStep.value), {"tsp": "%.1f" % ro.tempMlt, "amt": "%.1f" % (30 * ro.levelMlt)});
                # self._brewIO.writeOne(wo);
            # #
            # self.__debugSendButton = Button(self.__debugButtonFrame, command=debugSend, bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="Send", font=DEBUG_FONT);
            # self.__debugSendButton.pack(side=TOP, fill=X, padx=DEBUG_MARGIN, pady=DEBUG_MARGIN, ipadx=DEBUG_PADDING, ipady=DEBUG_PADDING);
            
            def resetTime():
                self.__schedule.startSeconds = time.time();
            #
            self.__debugResetButton = Button(self.__debugButtonFrame, command=resetTime, bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="Reset Time", font=DEBUG_FONT);
            self.__debugResetButton.pack(side=TOP, fill=X, padx=DEBUG_MARGIN, pady=DEBUG_MARGIN, ipadx=DEBUG_PADDING, ipady=DEBUG_PADDING);
            
            def addSecondsToTimeLeft(dt):
                self.__schedule.startSeconds += dt;
            #
            self.__debugAddMinuteButton = Button(self.__debugButtonFrame, command=lambda:addSecondsToTimeLeft(60), bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="+1 min", font=DEBUG_FONT);
            self.__debugAddMinuteButton.pack(side=TOP, fill=X, padx=DEBUG_MARGIN, pady=DEBUG_MARGIN, ipadx=DEBUG_PADDING, ipady=DEBUG_PADDING);
            
            self.__debugAddQuarterMinuteButton = Button(self.__debugButtonFrame, command=lambda:addSecondsToTimeLeft(15), bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="+15 sec", font=DEBUG_FONT);
            self.__debugAddQuarterMinuteButton.pack(side=TOP, fill=X, padx=DEBUG_MARGIN, pady=DEBUG_MARGIN, ipadx=DEBUG_PADDING, ipady=DEBUG_PADDING);
            
            self.__debugSubtractQuarterMinuteButton = Button(self.__debugButtonFrame, command=lambda:addSecondsToTimeLeft(-15), bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="-15 sec", font=DEBUG_FONT);
            self.__debugSubtractQuarterMinuteButton.pack(side=TOP, fill=X, padx=DEBUG_MARGIN, pady=DEBUG_MARGIN, ipadx=DEBUG_PADDING, ipady=DEBUG_PADDING);
            
            self.__debugSubtractMinuteButton = Button(self.__debugButtonFrame, command=lambda:addSecondsToTimeLeft(-60), bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="-1 min", font=DEBUG_FONT);
            self.__debugSubtractMinuteButton.pack(side=TOP, fill=X, padx=DEBUG_MARGIN, pady=DEBUG_MARGIN, ipadx=DEBUG_PADDING, ipady=DEBUG_PADDING);
            
            def endScheduleStep():
                self.__schedule.endCurrentActionItem = True;
            #
            self.__debugEndScheduleStepButton = Button(self.__debugButtonFrame, command=endScheduleStep, bd=5, relief=RAISED, bg=CC.white, fg=CC.black, text="End Step", font=DEBUG_FONT);
            self.__debugEndScheduleStepButton.pack(side=TOP, fill=X, padx=DEBUG_MARGIN, pady=DEBUG_MARGIN, ipadx=DEBUG_PADDING, ipady=DEBUG_PADDING);
            
        #
        
        
        #####################
        ## Schedule Screen ##
        #####################
        
        self.__scheduleFrame = ScreenFrame(self.__rootFrame, Page.schedule);
        self.__scheduleFrame.grid_rowconfigure(1, weight=1);
        self.__scheduleFrame.grid_columnconfigure(1, weight=1);
        
        self.__scheduleBoilTimeFrame = Frame(self.__scheduleFrame, bg=CC.gray_main);
        self.__scheduleBoilTimeFrame.grid(row=0, column=0, sticky=(W,E), padx=2, pady=2);
        
        self.__scheduleBoilTimeLabel = Label(self.__scheduleBoilTimeFrame, bg=CC.gray_main, fg="black", text="Boil Time:", font=CustomFonts.label);
        self.__scheduleBoilTimeLabel.pack(side=LEFT);

        self._scheduleBoilTimeText = Label(self.__scheduleBoilTimeFrame, bg=CC.gray_main, fg="black", text="[boil time]", font=CustomFonts.monoLarge);
        self._scheduleBoilTimeText.pack(side=LEFT, padx=10);
        
        self.__scheduleDataContainer = Frame(self.__scheduleFrame, bg=CC.gray_main); 
        self.__scheduleDataContainer.grid(row=1, column=0, sticky=(N,S,E,W), padx=2, pady=2);
        
        self._scheduleData = DataFrame("", [
            DataHeader("h3", "First-Wort Hops"),
            DataFrame("", [
                DataTable("BrewBoilAdditions", "BrewBoilAddition", CC.gray_menu, [
                    DataTableColumn("Type", "Type"),
                    DataTableColumn("Name", "Name"),
                    DataTableColumn("Use", "Use"),
                    DataTableColumn("Time", "Time", "min", E),
                    DataTableColumn("Amount", "Amount", "float-2", E),
                    DataTableColumn("Unit", "Unit")
                ], DataTableRowFilter("Use", "eq", "First Wort")),
            ]),
            DataHeader("h3", "Regular Boil Additions"),
            DataFrame("", [
                DataTable("BrewBoilAdditions", "BrewBoilAddition", CC.gray_menu, [
                    DataTableColumn("Type", "Type"),
                    DataTableColumn("Name", "Name"),
                    DataTableColumn("Use", "Use"),
                    DataTableColumn("Time", "Time", "min", E),
                    DataTableColumn("Amount", "Amount", "float-2", E),
                    DataTableColumn("Unit", "Unit")
                ], DataTableRowFilter("Use", "eq", "Boil")),
            ]),
            DataHeader("h3", "Flame-Out Hops"),
            DataFrame("", [
                DataTable("BrewBoilAdditions", "BrewBoilAddition", CC.gray_menu, [
                    DataTableColumn("Type", "Type"),
                    DataTableColumn("Name", "Name"),
                    DataTableColumn("Use", "Use"),
                    DataTableColumn("Time", "Time", "min", E),
                    DataTableColumn("Amount", "Amount", "float-2", E),
                    DataTableColumn("Unit", "Unit")
                ], DataTableRowFilter("Use", "eq", "Aroma")),
            ])
        ], 0);
        self._scheduleData.build(self.__scheduleDataContainer);
        
        # self.__scheduleNotificationsLabel = Label(self.__scheduleFrame, bg=CC.gray_main, fg="black", text="Notifications:", font=CustomFonts.label);
        # self.__scheduleNotificationsLabel.grid(row=0, column=1, sticky=W, padx=2, pady=2);
        
    #
    
    @staticmethod
    def getTempBarColor(temperature):
        # hue 240 = blue, hue 360 = red
        rangedTemp = keepInRange(temperature, 0, 240); # this will be between 0 and 240
        hue = rangedTemp / 2.0; # this will be between 0 and 120
        hue += 240; # this will be between 240 and 360
        rgb = colorsys.hls_to_rgb(hue/360, 0.50, 0.75);
        result = "#%02x%02x%02x" % (int(256*rgb[0]), int(256*rgb[1]), int(256*rgb[2]));
        return result;
    #
    
    @staticmethod
    def getTempBarColor2(temperature):
        # hue 240 = blue, hue 360 = red
        temperatureC = convertFtoC(temperature);
        rangedTemp = keepInRange(temperatureC, 0, 100); # this will be between 0 and 100
        hue = rangedTemp / 100.0; # this will be between 0 and 1
        # hue = (((hue-1/2)^(1/3))/((1/2)^(1/3)) + 1) / 2
        hue = ((cuberoot(hue - 0.5))/0.7937 + 1) / 2; # this will also be between 0 and 1
        hue *= 240; # this will be between 0 and 240
        hue = 240 - hue; # this will be between 240 and 0
        rgb = colorsys.hls_to_rgb(hue/360, 0.50, 0.75);
        result = "#%02x%02x%02x" % (int(256*rgb[0]), int(256*rgb[1]), int(256*rgb[2]));
        return result;
    #
    
    @staticmethod
    def getTempBarColor3(temperature):
        # hue 240 = blue, hue 360 = red
        temperatureC = convertFtoC(temperature);
        rangedTemp = keepInRange(temperatureC, 0, 100); # this will be between 0 and 100
        hue = rangedTemp / 100.0; # this will be between 0 and 1
        hue = hue**0.5; # this will also be between 0 and 1
        hue = hue * 180; # this will be between 0 and 180
        hue = 180 - hue; # this will be between 180 and 0
        rgb = colorsys.hls_to_rgb(hue/360, 0.50, 0.75);
        result = "#%02x%02x%02x" % (int(256*rgb[0]), int(256*rgb[1]), int(256*rgb[2]));
        return result;
    #
    
    @staticmethod
    def getTimeLeftColor(percentLeft):
        result = CC.black;
        if 0.5 < percentLeft: result = CC.olive;
        elif 0.25 < percentLeft: result = CC.orange;
        elif 0.0 < percentLeft: result = CC.red;
        return result;
    #
    
    def updateSystemInfo(self):
        ro = self._currentRO;
        #self.__stepText.config(text=str(ro.brewStep));
        self.__levelHltText.config(text="%.1f%%" % (100 * ro.levelHlt));
        self.__levelMltText.config(text="%.1f%%" % (100 * ro.levelMlt));
        self.__levelBkText.config(text="%.1f%%" % (100 * ro.levelBk));
        self.__levelHltBar.config(height=((CONTAINER_INNER_HEIGHT - self.__levelHltText.winfo_height()) * ro.levelHlt));
        self.__levelMltBar.config(height=((CONTAINER_INNER_HEIGHT - self.__levelMltText.winfo_height()) * ro.levelMlt));
        self.__levelBkBar.config(height=((CONTAINER_INNER_HEIGHT - self.__levelBkText.winfo_height()) * ro.levelBk));
        self.__tempHltText.config(text="%s F" % ro.tempHlt);
        self.__tempMltText.config(text="%s F" % ro.tempMlt);
        self.__tempBkText.config(text="%s F" % ro.tempBk);
        self.__tempHltBar.config(height=((CONTAINER_INNER_HEIGHT - self.__tempHltText.winfo_height()) * (convertFtoC(ro.tempHlt)/100)), bg=BrewInterface.getTempBarColor3(ro.tempHlt));
        self.__tempMltBar.config(height=((CONTAINER_INNER_HEIGHT - self.__tempMltText.winfo_height()) * (convertFtoC(ro.tempMlt)/100)), bg=BrewInterface.getTempBarColor3(ro.tempMlt));
        self.__tempBkBar.config(height=((CONTAINER_INNER_HEIGHT - self.__tempBkText.winfo_height()) * (convertFtoC(ro.tempBk)/100)), bg=BrewInterface.getTempBarColor3(ro.tempBk));
    #
    
    def updateTimeLeft(self):
        timeText = convertSecondsToMmSs(self.__schedule.clockSecondsMax);
        self.__timeMaxText.config(text=("out of " + timeText));
        
        timeLeft = self.__schedule.getTimeSecondsLeft();
        
        percentLeft = 0 if (0 == self.__schedule.clockSecondsMax) else (timeLeft / self.__schedule.clockSecondsMax);
        clockColor = BrewInterface.getTimeLeftColor(percentLeft);
        self.__clockCanvas.itemconfig(self.__timePercentArc, extent=(360*percentLeft), outline=clockColor);
        
        percentSecondsLeft = (timeLeft % 60) / 60;
        self.__clockCanvas.itemconfig(self.__secondsArc, extent=(360*percentSecondsLeft), outline=clockColor);
        
        timeLeftText = convertSecondsToMmSs(timeLeft);
        self.__clockCanvas.itemconfig(self.__timeLeftText, text=timeLeftText);
    #
    
    def updateDisplay(self):
        try:
            self._currentRO = self._brewIO.readOne();
            self.updateSystemInfo(); # read-object information
            self.updateTimeLeft(); # time left
        #
        finally:
            if 0 == self._brewIO.readsLeft():
                self.after(self._brewIO.refreshMillis, self.updateDisplay);
            #
            else:
                self.updateDisplay(); # update immediately if more read objects are in the read queue
            #
        #
    #
    
    def startApp(self):
        self.title(APP_TITLE);
        self.attributes("-fullscreen", True);
        #self.iconphoto(self._w, PhotoImage(file="resources/beer-icon.png"));
        
        MenuButton.pageSelectionEvent.publish(Page.recipe); # choose default tab
        
        self._brewIO.open();
        self.updateDisplay();
        self.mainloop();
    #
#

if __name__ == '__main__':
    print (APP_TITLE + " initializing...");
    app = BrewInterface();
    print ("done.");
    app.startApp();
#