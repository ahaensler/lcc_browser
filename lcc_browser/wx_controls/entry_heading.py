import wx

class EntryHeading(wx.StaticText):
    # shows bold heading and tooltip about memory space and address
    def __init__(self, parent, name, entry):
        super().__init__(parent, wx.ID_ANY, name)
        self.Bind(wx.EVT_MOTION, self.on_enter)
        self.SetLabelMarkup(f"<b>{name}</b>")
        self.Wrap(700)
        self.entry = entry
        self.SetToolTip(wx.ToolTip(""))

    def on_enter(self, evt):
        address = self.entry.get_address()
        address = "-NA-" if address is None else f"0x{address:X}"
        self.GetToolTip().SetTip(f"space=0x{self.entry.space:X}, address={address}, size=0x{self.entry.size:X}")
