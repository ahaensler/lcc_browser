from lcc_browser.templates.settings import SettingsDialogTemplate
import wx
import os
from urllib.parse import urlparse
from urllib.request import url2pathname
import pathlib
from lcc_browser.lcc.lcc_protocol import id_to_bytes

class SimpleValidator(wx.Validator):
    def Clone(self):
        return self.__class__()

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

class NodeIdValidator(SimpleValidator):
    def Validate(self, win):
        text_ctrl = self.GetWindow()
        text = text_ctrl.GetValue()
        node_id = id_to_bytes(text)
        is_valid = node_id is not None and len(node_id) == 6
        if not is_valid:
            wx.MessageDialog(win, "Node ID should be a hex string, like 001122334455", "Error").ShowModal()
        return is_valid

class FilenameValidator(SimpleValidator):
    def Validate(self, win):
        text_ctrl = self.GetWindow()
        path = text_ctrl.GetValue()
        path = os.path.abspath(path)
        is_valid = os.path.exists(path) and not os.path.isdir(path)
        if not is_valid:
            wx.MessageDialog(win, f"Filename \"{path}\" is not a valid HTML file.", "Error").ShowModal()
        return is_valid

class SettingsDialog(SettingsDialogTemplate):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.node_id.SetValidator(NodeIdValidator())
        self.node_id.SetValue(settings.get("node_id"))
        self.html_path.SetValidator(FilenameValidator())
        print(settings.get("html_path"))
        p = urlparse(settings.get("html_path"))
        html_path = url2pathname(p.path) # fix leading slash in Windows
        html_path = os.path.abspath(os.path.join(p.netloc, html_path))
        print(p.netloc, p.path)
        print(html_path)
        self.html_path.SetValue(html_path)
        self.auto_connect.SetValue(settings.get("auto_connect", False))

    def get_settings(self):
        html_path = self.html_path.GetValue()
        html_path = os.path.abspath(html_path)
        html_path = pathlib.Path(html_path).as_uri()

        settings = {
            "node_id": self.node_id.GetValue(),
            "html_path": html_path,
            "auto_connect": self.auto_connect.IsChecked(),
        }
        return settings

    def on_choose_html_path(self, evt):
        d = wx.FileDialog(self, "Select HTML file", wildcard="HTML files (*.html)|*.htm;*.html|All files|*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if d.ShowModal() == wx.ID_CANCEL:
            return

        html_path = d.GetPath()
        self.html_path.SetValue(html_path)
