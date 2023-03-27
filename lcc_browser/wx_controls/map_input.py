import wx
from lcc_browser.wx_controls.tool_button import ToolButton

class MapControl(wx.Choice):
    def __init__(self, parent, choices, datatype=str):
        # takes a key value dictionary where values are displayed to the user
        self.choices = {datatype(k): v for k, v in choices.items()}
        self.datatype = datatype
        self.key_to_idx = {datatype(x): i for i, x in enumerate(choices.keys())}
        super().__init__(parent, choices=list(choices.values()))

    def GetValue(self):
        idx = self.GetSelection()
        if idx == wx.NOT_FOUND: return None
        return list(self.choices.keys())[idx]

    def SetValue(self, val):
        idx = self.key_to_idx.get(self.datatype(val))
        if idx is None:
            print("Invalid key for map", val)
        else:
            self.SetSelection(idx)

class MapInput(wx.Panel):
    def __init__(self, parent, choices, cdi_entry, default, datatype):
        super().__init__(parent)
        self.SetToolTip(wx.ToolTip(""))
        self.initial_value = -1
        self.default_value = default
        self.cdi_entry = cdi_entry

        self.input = MapControl(self, choices, datatype)
        self.input.Bind(wx.EVT_CHOICE, self.on_choice)
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

        self.info_text = wx.StaticText(self, wx.ID_ANY)
        self.info_text.SetMinSize((400, wx.DefaultCoord))
        sizer.Add(self.info_text, 1, border=5, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)

        self.SetSizer(sizer)

    def on_choice(self, evt=None):
        if self.input.GetSelection() == wx.NOT_FOUND:
            self.GetToolTip().SetTip("Make a selection")
            self.input.SetBackgroundColour(wx.NullColour)
        else:
            is_modified = self.input.GetValue() != self.initial_value
            if is_modified:
                self.GetToolTip().SetTip("Ready for upload to node")
                self.input.SetBackgroundColour(wx.YELLOW)
            else:
                self.GetToolTip().SetTip("Value present on node")
                self.input.SetBackgroundColour(wx.NullColour)

    def GetValue(self):
        return self.input.GetValue()

    def SetValue(self, val):
        self.initial_value = val
        idx = self.input.key_to_idx.get(val)
        if idx is None:
            self.info_text.SetLabel(f"Node returned an invalid value '{val}'")
            self.input.SetSelection(wx.NOT_FOUND)
            self.on_choice()
            return

        self.info_text.SetLabel("")
        self.input.SetValue(val)
        self.on_choice()

    def on_default(self, evt):
        self.input.SetValue(self.default_value)
        self.on_choice()

    def on_write(self, evt):
        val = self.input.GetValue().to_bytes(self.cdi_entry.size, byteorder="big")
        self.cdi_entry.write(val)

    def on_read(self, evt):
        self.cdi_entry.read()

    def set_raw_value(self, val):
        assert len(val) == self.cdi_entry.size
        val = int.from_bytes(val, byteorder="big")
        self.SetValue(val)
        self.initial_value = val
        self.on_choice()

