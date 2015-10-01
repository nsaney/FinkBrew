# import sys;
# if sys.version_info[0] < 3:
# #
# else:
# #
import smtplib;
import threading;


###################
###             ###
###  Functions  ###
###             ###
###################

def keepInRange(value, min, max):
    result = value;
    if min > max: result = keepInRange(value, max, min);
    elif value < min: result = min;
    elif value > max: result = max;
    return result;
#

def isWithinTolerance(value, centerValue, upTolerance, downTolerance=None):
    downTolerance = (-1 * upTolerance) if None == downTolerance else downTolerance;
    result = False;
    if ((centerValue + downTolerance) <= value and value <= (centerValue + upTolerance)): result = True;
    return result;
#

def convertFtoC(valueF):
    return (valueF - 32) * (5.0 / 9.0);
#

def convertCtoF(valueC):
    return (valueC * (9.0 / 5.0)) + 32;
#

def convertKgToOz(valueKg):
    return valueKg * 35.274;
#

def convertLtoTsp(valueL):
    return valueL * 202.884;
#

ONE_THIRD = 1/3.;
def cuberoot(value):
    value = float(value);
    return -((-value)**ONE_THIRD) if value < 0 else (value**ONE_THIRD);
#

def convertSecondsToMmSs(valueSeconds, minuteFormat="%d"):
    minutes = int(valueSeconds / 60);
    secondsMod = int(valueSeconds % 60);
    return (minuteFormat + ":%02d") % (minutes, secondsMod);
#

def showXmlDebug(xelement, level=0):
    if xelement == None: return "";
    result = "";
    indent = "  " * level;
    tag = xelement.tag;
    text = str(xelement.text if (0 == len(xelement)) else "");
    result += "%s{tag: %s, text: %s}" % (indent, tag, text);
    for xchild in xelement:
        result += "\n" + showXmlDebug(xchild, level + 1);
    #
    return result;
#

def sendSimpleMail(smtpHost, smtpUsername, smtpPassword, fromAddress, toAddresses, message):
    if not toAddresses: 
        return;
    #
    
    # this portion of the code based heavily on: https://github.com/CrakeNotSnowman/Python_Message/blob/master/sendMessage.py
    server = smtplib.SMTP(smtpHost);
    server.starttls();
    if smtpUsername and smtpPassword:
        server.login(smtpUsername, smtpPassword);
    #
    server.sendmail(fromAddress, toAddresses, message);
    server.quit();
#

def sendSimpleMailAsync(*mailArgs):
    sendThread = threading.Thread(target=sendSimpleMail, args=mailArgs);
    sendThread.start();
#


#################
###           ###
###  Classes  ###
###           ###
#################

class CC:
    """Static-ish class for colors, a la colors.css."""
    #blues
    navy = "#001f3f";
    blue = "#0074d9";
    aqua = "#7fdbff";
    teal = "#39cccc";
    #greens
    olive = "#3d9970";
    green = "#2ecc40";
    lime = "#01ff70";
    #warms
    yellow = "ffdc00";
    orange = "#ff851b";
    red = "#ff4136";
    fuchsia = "#f012be";
    purple = "#b10dc9";
    maroon = "#85144b";
    #grayscale
    white = "#ffffff";
    silver = "#dddddd";
    gray = "#aaaaaa";
    black = "#111111";
#

class CustomEvent:
    """Handles events."""
    callbacks = [];
    def publish(self, arg1):
        for callback in self.callbacks: callback(arg1);
    
    def subscribe(self, callback):
        self.callbacks.append(callback);
    
    def unsubscribe(self, callback):
        if callback in self.callbacks: self.callbacks.remove(callback);
#