import sys;
if sys.version_info[0] < 3:
    from Tkinter import *;
#
else:
    from tkinter import *;
#
import xml.etree.ElementTree as ElementTree;

#####################
## THINGS NOT MINE ##
#####################

# stolen so hard from:  http://tkinter.unpythonic.net/wiki/VerticalScrolledFrame
class VerticalScrolledFrame(Frame):
    """A pure Tkinter scrollable frame that actually works!

    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling
    
    """
    def __init__(self, parent, *args, **kw):
        Frame.__init__(self, parent, *args, **kw)            

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        self.canvas = canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)

        return
#

#################
## THINGS MINE ##
#################

class DataSettings():
    """Static-ish class for settings."""
    scaling = 1.0;
    
    @staticmethod
    def scale(n): return int(DataSettings.scaling * n);
#

class DataFrame():
    """Used for binding xml data to a tkinter structure."""
    def __init__(self, _data, _children, _padxLeft=48):
        self.data = _data;
        self.children = _children;
        self.padxLeft = _padxLeft;
        self.widget = None;
    #
    def build(self, parent):
        if not self.widget:
            self.widget = Frame(parent, bg=parent["bg"]);
            self.widget.pack(anchor=NW, side=TOP, padx=(self.padxLeft, 0));
            for child in self.children: child.build(self.widget);
        #
        return self.widget;
    #
    def bind(self, xelement):
        if self.widget:
            for child in self.children:
                xchild = xelement.find(child.data);
                child.bind(xchild if xchild != None else xelement);
            #
        #
    #
#

class DataHeader():
    sizeMap = { "h1": 24, "h2": 18, "h3": 14, "h4": 12, "h5": 10, "h6": 8 };
    def __init__(self, _size, _text):
        self.data = "";
        self.size = DataHeader.sizeMap[_size];
        self.text = _text;
        self.widget = None;
    #
    def build(self, parent):
        if not self.widget:
            padxLeft = 48 - (2 * self.size);
            self.widget = Label(parent, bg=parent["bg"], text=self.text, font=("Arial", DataSettings.scale(self.size), "bold"));
            self.widget.pack(anchor=NW, side=TOP, padx=(padxLeft, 0), pady=(8, 0));
        #
        return self.widget;
    #
    def bind(self, xelement): 
        pass;
    #
#

class DataLabel():
    def __init__(self, _text):
        self.data = "";
        self.text = _text;
        self.widget = None;
    #
    def build(self, parent):
        if not self.widget:
            self.widget = Label(parent, bg=parent["bg"], text=self.text, font=("Arial", DataSettings.scale(10), "bold"));
            self.widget.pack(anchor=NW, side=LEFT);
        #
        return self.widget;
    #
    def bind(self, xelement): 
        pass;
    #
#

class DataValue():
    formatters = {
        "string": lambda s: s,
        "*1000": lambda s: "%.2f" % (float(s) * 1000),
        "C": lambda s: "%.1f C" % float(s),
        "days": lambda s: "%.2f days" % float(s),
        "F-from-C": lambda s: "%.1f F" % (32 + (float(s) * 9.0 / 5.0)),
        "float-1": lambda s: "%.1f" % float(s),
        "float-2": lambda s: "%.2f" % float(s),
        "g-from-kg": lambda s: "%.2f g" % (float(s) * 1000),
        "g-or-mL": lambda s: "g" if s.upper() == "TRUE" else "mL",
        "gal-from-L": lambda s: "%.2f gal" % (float(s) / 3.78541),
        "kg": lambda s: "%.2f kg" % float(s),
        "kg-or-L": lambda s: "kg" if s.upper() == "TRUE" else "L",
        "L": lambda s: "%f L" % float(s),
        "lb-from-kg": lambda s: "%.2f lb" % (float(s) * 2.20462),
        "mL-from-L": lambda s: "%.2f mL" % (float(s) * 1000),
        "min": lambda s: ("%f" % float(s)).rstrip("0").rstrip(".") + " min",
        "oz-from-kg": lambda s: "%.2f oz" % (float(s) * 35.274),
        "percent": lambda s: "%.2f%%" % float(s),
        "percent-2": lambda s: "%.2f%%" % float(s),
        "pH": lambda s: "%.2f pH" % float(s),
        "ppm": lambda s: "%.1f ppm" % float(s),
        "tsp-from-L": lambda s: "%.2f tsp" % (float(s) * 202.884),
    };
    def __init__(self, _data, _formatterName="string"):
        self.data = _data;
        self.formatter = DataValue.formatters[_formatterName];
        self.widget = None;
    #
    def build(self, parent):
        if not self.widget:
            self.widget = Label(parent, bg=parent["bg"], text="", font=("Courier", DataSettings.scale(10), "normal"));
            self.widget.pack(anchor=NW, side=LEFT, padx=(0,20));
        #
        return self.widget;
    #
    def bind(self, xelement):
        if self.widget:
            boundText = xelement.text if xelement != None else "";
            boundText = str(boundText).strip();
            formattedText = "";
            try: formattedText = self.formatter(boundText) if boundText else "[none]";
            except: formattedText = "[error]";
            self.widget.config(text=formattedText);
        #
    #
#

class DataTable():
    def __init__(self, _data, _rowData, _headerBg, _columns, _rowFilter=None):
        self.data = _data;
        self.rowData = _rowData;
        self.headerBg = _headerBg;
        self.columns = _columns;
        self.rowFilter = _rowFilter;
        self.widget = None;
        self.widgetChildren = [];
    #
    def build(self, parent):
        if not self.widget:
            self.widget = Frame(parent, bg=parent["bg"]);
            self.widget.pack(anchor=NW, side=TOP);
            colNumber = 0;
            for column in self.columns:
                th = Label(self.widget, bg=self.headerBg, text=column.title, font=("Arial", DataSettings.scale(10), "bold"));
                th.grid(row=0, column=colNumber, sticky=(W,E), ipadx=10);
                colNumber += 1;
            #
            border = Frame(self.widget, bg="#000000", height=1)
            border.grid(row=1, column=0, columnspan=colNumber, sticky=(W,E));
        #
        return self.widget;
    #
    def bind(self, xelement):
        if self.widget:
            for widgetChild in self.widgetChildren:
                widgetChild.grid_forget();
                widgetChild.destroy();
            #
            self.widgetChildren = [];
            
            xrows = xelement.findall(self.rowData);
            if self.rowFilter: xrows = [xrow for xrow in xrows if self.rowFilter.test(xrow)];
            if not xrows: xrows = [ElementTree.Element("__Empty__")];
            rowNumber = 2;
            for xrow in xrows:
                colNumber = 0;
                for column in self.columns:
                    td = Label(self.widget, bg=self.widget["bg"], text=column.getText(xrow), font=("Courier", DataSettings.scale(10), "normal"));
                    td.grid(row=rowNumber, column=colNumber, sticky=column.sticky, ipadx=10);
                    self.widgetChildren.append(td);
                    colNumber += 1;
                #
                border = Frame(self.widget, bg="#000000", height=1)
                border.grid(row=(rowNumber+1), column=0, columnspan=colNumber, sticky=(W,E));
                self.widgetChildren.append(border);
                rowNumber += 2;
            #
        #
    #
#

class DataTableColumn():
    def __init__(self, _title, _data, _formatterName="string", _sticky=W):
        self.title = _title;
        self.data = _data;
        self.formatter = DataValue.formatters[_formatterName];
        self.sticky = _sticky;
    #
    def getText(self, xrow):
        xcolumn = xrow.find(self.data);
        boundText = xcolumn.text if xcolumn != None else "";
        boundText = str(boundText).strip();
        formattedText = "";
        try: formattedText = self.formatter(boundText) if boundText else "[none]";
        except: formattedText = "[error]";
        return formattedText;
    #
#

class DataTableRowFilter():
    ops = {
        "eq": lambda x, y: str(x).lower() == str(y).lower(),
        "neq": lambda x, y: str(x).lower() != str(y).lower(),
    };
    def __init__(self, _data, _opName, _value):
        self.data = _data;
        self.op = DataTableRowFilter.ops[_opName];
        self.value = _value;
    #
    def test(self, xelement):
        result = False;
        xchild = xelement.find(self.data);
        if xchild != None:
            result = self.op(xchild.text, self.value);
        #
        return result;
    #
#