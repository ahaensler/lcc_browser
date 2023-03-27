import wx
from lcc_browser.templates.connection_dialog import ConnectionDialogTemplate
import lcc_browser.can

class ConnectionDialog(ConnectionDialogTemplate):
    def __init__(self, parent, protocol):
        super().__init__(parent)
        self.protocol = protocol
        self.connection = None
        self.drivers = list(lcc_browser.can.can_drivers.values())
        self.driver_selection.Bind(wx.EVT_CHOICE, self.on_driver_selected)
        for CanInterface in self.drivers:
            self.driver_selection.Append(CanInterface.name)
            

    def on_driver_selected(self, evt):
        idx = self.driver_selection.GetSelection()
        if idx == wx.NOT_FOUND: return
        self.connection = self.drivers[idx](self.protocol)

        panel = self.connection.create_parameters_panel(self)
        self.sizer.Replace(self.parameters_panel, panel)
        self.parameters_panel = panel
        self.sizer.Fit(self)
        self.Layout()
