import wx
import re
from lcc_browser.lcc.lcc_protocol import id_to_bytes
from lcc_browser.wx_controls.tool_button import ToolButton

def validate_partial(text):
    is_match = re.match("^[0-9a-fA-F\.]+$", text)
    if not is_match: return
    event_id = text.replace(".", "")
    return len(event_id) <= 8*2

def validate_full(text):
    event_id = id_to_bytes(text)
    if event_id is None: return False
    is_valid = event_id is not None and len(event_id) == 8
    return is_valid

class EventIdInput(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.input = wx.TextCtrl(self)

        self.input.SetMinSize((200, wx.DefaultCoord))
        self.SetToolTip(wx.ToolTip(""))
        self.input.Bind(wx.EVT_CHAR, self.on_char)
        self.input.Bind(wx.EVT_TEXT, self.on_text)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.input)

        self.read_button = ToolButton(self, wx.ART_FIND, "Read from node")
        sizer.Add(self.read_button, border=5, flag=wx.LEFT)
        self.read_button.Bind(wx.EVT_BUTTON, self.on_read)

        self.write_button = ToolButton(self, wx.ART_FILE_SAVE, "Write to node")
        sizer.Add(self.write_button, border=5, flag=wx.LEFT)
        self.write_button.Bind(wx.EVT_BUTTON, self.on_write)
        
        self.SetSizer(sizer)
        self.initial_value = None

    def on_char(self, evt):
        keycode = evt.GetKeyCode()
        c = chr(keycode)
        if keycode < 255 and c.isprintable():
            text = self.input.GetValue() + chr(keycode)
            if not validate_partial(text):
                return
        evt.Skip()

    def on_text(self, evt=None):
        text = self.input.GetValue()
        if not validate_full(text):
            self.GetToolTip().SetTip("Invalid")
            self.input.SetBackgroundColour(wx.LIGHT_GREY)
        else:
            if self.GetValue() != self.initial_value:
                self.GetToolTip().SetTip("Ready for upload to node")
                self.input.SetBackgroundColour(wx.YELLOW)
            else:
                self.GetToolTip().SetTip("Value present on node")
                self.input.SetBackgroundColour(wx.NullColour)

    def SetValue(self, text):
        self.input.SetValue(text)
        self.initial_value = self.GetValue()
        self.on_text()

    def GetValue(self):
        text = self.input.GetValue()
        if not validate_full(text): return None
        return id_to_bytes(text)

    def on_write(self, evt):
        val = self.GetValue()
        if val is None:
            dlg = wx.MessageDialog(self, f"Item {self.cdi_entry.name} is invalid and will not be written.", "Error", wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            return None
        self.cdi_entry.write(val)

    def on_read(self, evt):
        self.cdi_entry.read()

    def set_raw_value(self, val):
        assert len(val) == 8
        val = val.hex()
        val = val[:6*2] + "." + val[6*2:]
        self.SetValue(val)
        self.on_text()
