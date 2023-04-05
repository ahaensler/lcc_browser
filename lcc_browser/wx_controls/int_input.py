import wx
from lcc_browser.wx_controls.tool_button import ToolButton

class IntInput(wx.Panel):
    def __init__(self, parent, min, max, default):
        super().__init__(parent)
        self.SetToolTip(wx.ToolTip(""))

        self.input = wx.SpinCtrl(self, min=0, max=0xffff)
        self.input.SetMinSize((150, wx.DefaultCoord))
        self.min = min
        self.max = max

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.input)

        self.read_button = ToolButton(self, wx.ART_FIND, "Read from node")
        sizer.Add(self.read_button, border=5, flag=wx.LEFT)
        self.read_button.Bind(wx.EVT_BUTTON, self.on_read)

        if default is not None:
            self.default_button = ToolButton(self, wx.ART_UNDO, "Set to default")
            sizer.Add(self.default_button, border=5, flag=wx.LEFT)
            self.default_button.Bind(wx.EVT_BUTTON, self.on_default)

        self.write_button = ToolButton(self, wx.ART_FILE_SAVE, "Write to node")
        sizer.Add(self.write_button, border=5, flag=wx.LEFT)
        self.write_button.Bind(wx.EVT_BUTTON, self.on_write)
        
        if min is not None or max is not None:
            if min is None: min = ""
            if max is None: max = ""
            label = wx.StaticText(self, wx.ID_ANY, f"Valid from {min} to {max}")
            sizer.Add(label, border=5, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)
        self.SetSizer(sizer)

        self.input.Bind(wx.EVT_SPINCTRL, self.on_change)
        self.input.Bind(wx.EVT_KEY_UP, self.on_change)
        self.default_value = default
        self.initial_value = None

    def validate(self):
        val = self.input.GetValue()
        max_ok = val >= self.min if self.min else 1
        min_ok = val <= self.max if self.max else 1
        return max_ok and min_ok

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

    def on_default(self, evt):
        self.input.SetValue(self.default_value)
        self.on_change()

    def on_write(self, evt):
        val = self.input.GetValue()
        if not self.validate():
            dlg = wx.MessageDialog(self, f"Item {self.cdi_entry.name} is out of range ({val}). Continue?", "Warning", wx.YES_NO | wx.CANCEL)
            if dlg.ShowModal() != wx.ID_YES: return None
        val = val.to_bytes(self.cdi_entry.size, 'big')
        self.cdi_entry.write(val)

    def on_read(self, evt):
        self.cdi_entry.read()

    def set_raw_value(self, val):
        assert len(val) == self.cdi_entry.size
        val = int.from_bytes(val, byteorder="big")
        self.initial_value = val
        wx.CallAfter(self.SetValue, val)
        wx.CallAfter(self.on_change)
