import wx
from lcc_browser.wx_controls.tool_button import ToolButton

class StringInput(wx.Panel):
    def __init__(self, parent, size):
        super().__init__(parent)
        self.SetToolTip(wx.ToolTip(""))

        self.input = wx.TextCtrl(self)
        self.input.SetMinSize((500, wx.DefaultCoord))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.input)

        self.read_button = ToolButton(self, wx.ART_FIND, "Read from node")
        sizer.Add(self.read_button, border=5, flag=wx.LEFT)
        self.read_button.Bind(wx.EVT_BUTTON, self.on_read)

        self.write_button = ToolButton(self, wx.ART_FILE_SAVE, "Write to node")
        sizer.Add(self.write_button, border=5, flag=wx.LEFT)
        self.write_button.Bind(wx.EVT_BUTTON, self.on_write)

        label = wx.StaticText(self, wx.ID_ANY, f"Max length {size-1}")
        sizer.Add(label, border=5, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)
        
        self.SetSizer(sizer)

        self.input.Bind(wx.EVT_TEXT, self.on_change)
        self.input.Bind(wx.EVT_KEY_UP, self.on_change)
        self.initial_value = None

    def validate(self):
        val = self.input.GetValue().encode("utf-8")
        return len(val) < self.cdi_entry.size - 1 # null-terminated string

    def on_change(self, evt=None):
        if not self.validate():
            self.GetToolTip().SetTip("Invalid")
            self.input.SetBackgroundColour(wx.LIGHT_GREY)
        else:
            is_modified = self.input.GetValue() != self.initial_value
            if is_modified:
                self.GetToolTip().SetTip("Ready for upload to node")
                self.input.SetBackgroundColour(wx.YELLOW)
            else:
                self.GetToolTip().SetTip("Value present on node")
                self.input.SetBackgroundColour(wx.NullColour)
        self.Refresh()

    def SetValue(self, val):
        self.initial_value = val
        self.input.SetValue(val)
        self.on_change()

    def GetValue(self):
        if not self.validate(): return None
        return self.input.GetValue()

    def on_write(self, evt):
        if not self.validate():
            dlg = wx.MessageDialog(self, f"Item {self.cdi_entry.name} is invalid and will not be written.", "Error", wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            return None
        val = self.input.GetValue().encode("utf-8")
        val += bytes(self.cdi_entry.size - len(val)) # fill with zeros
        self.cdi_entry.write(val)

    def on_read(self, evt):
        self.cdi_entry.read()

    def set_raw_value(self, val):
        try:
            idx = val.index(0)
            val = val[:idx].decode("utf-8")
            self.SetValue(val)
            self.initial_value = val
            self.on_change()
        except ValueError:
            print("Encountered invalid string memory value", val)
            self.SetValue("")
