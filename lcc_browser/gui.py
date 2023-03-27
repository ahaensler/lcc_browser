import wx
import wx.html2
import json
from lcc_browser.lcc.lcc_protocol import LccProtocol
from lcc_browser.templates.gui import *
from lcc_browser.log_viewer import *
from lcc_browser.lcc_nodes_viewer import *
from lcc_browser.connection_dialog import *
from lcc_browser.settings_dialog import *
from lcc_browser.settings import settings
from lcc_browser.wx_events import *

js_lcc_injection = """
class LCCEventTarget extends EventTarget {
  sendEvent(node_name, event_data) {
    window.LCC.postMessage({type: "event", node_name, ...event_data});
  }
  sendRawEvent(id) {
    window.LCC.postMessage({type: "raw-event", id});
  }
}
const LCC = new LCCEventTarget();
"""


class GuiFrame(OpenLcbGui):
    def __init__(self):
        super().__init__(None, title="OpenLcb Interface")
        self.connection = None
        self.Bind(EVT_CAN_FRAME_IN, self.on_can_frame_in)
        self.Bind(EVT_LCC, self.on_lcc)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.lcc = LccProtocol()

        self.can_viewer = LogViewer(self, "CAN Traffic")
        self.can_viewer.Bind(wx.EVT_CLOSE, self.on_can_viewer_close)
        self.can_viewer.Hide()

        self.lcc_viewer = LogViewer(self, "LCC Traffic")
        self.lcc_viewer.Bind(wx.EVT_CLOSE, self.on_lcc_viewer_close)
        self.lcc_viewer.Hide()

        self.lcc_nodes = LccNodesViewer(self)
        self.lcc_nodes.Bind(wx.EVT_CLOSE, self.on_lcc_nodes_close)
        self.lcc_nodes.Hide()

        self.browser = wx.html2.WebView.New(self.panel)
        self.sizer.Add(self.browser, 1, wx.EXPAND)
        result = self.browser.AddUserScript(js_lcc_injection, wx.html2.WEBVIEW_INJECT_AT_DOCUMENT_START)
        assert result
        self.browser.EnableAccessToDevTools()
        self.browser.AddScriptMessageHandler('LCC')
        self.browser.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self.on_browser_event)
        self.browser.Bind(wx.html2.EVT_WEBVIEW_ERROR, self.on_browser_error)

        self.statusbar = self.CreateStatusBar(1, wx.STB_DEFAULT_STYLE)
        self.statusbar.SetStatusText("Not connected")

    def on_browser_event(self, evt):
        evt = json.loads(evt.GetString())
        if evt.get("type") == "raw-event":
            self.lcc.emit_event(evt["id"])
        elif evt.get("type") == "event":
            # todo, generate event id from higher-level representation
            pass

    def on_browser_error(self, evt):
        print("Browser error", evt.GetString())

    def reload_browser(self, evt):
        if self.browser.GetCurrentURL() != settings["html_path"]:
            self.browser.LoadURL(settings["html_path"])
        else:
            self.browser.Reload(wx.html2.WEBVIEW_RELOAD_NO_CACHE)

    def establish_connection(self, evt):
        dialog = ConnectionDialog(self, self.lcc)
        if dialog.ShowModal() == wx.ID_CANCEL: return

        params = dialog.connection.get_parameters()
        self.connect(dialog.connection, params)

    def connect(self, connection, parameters):
        self.disconnect()
        self.connection = connection
        try:
            self.connection.connect(parameters)
        except Exception as e:
            dlg = wx.MessageDialog(self, f"CAN driver didn't connect: {str(e)}", "Error", wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            return

        self.lcc.set_frame_callback(lambda frame, sent_by_us: wx.PostEvent(self, LccEvent(frame=frame, sent_by_us=sent_by_us)))
        self.connection.set_frame_callback(lambda frame, sent_by_us: wx.PostEvent(self, CanFrameInEvent(frame=frame, sent_by_us=sent_by_us)))
        self.connection.start()
        self.lcc.connection = self.connection
        self.lcc.reserve_node_alias()
        self.statusbar.SetStatusText("Connected")
        settings['can_driver'] = self.connection.name
        settings['can_driver_params'] = parameters

    def on_close(self, evt):
        settings.save()
        self.disconnect()
        evt.Skip()

    def disconnect(self, evt=None):
        self.lcc.join()
        if self.connection:
            self.connection.join()
            self.connection.disconnect()
        self.statusbar.SetStatusText("Not connected")

    def on_can_frame_in(self, evt):
        log_entry = str(evt.frame)
        if evt.sent_by_us:
            log_entry += " (this node)"
        wx.PostEvent(self.can_viewer, LogEntryEvent(get_log_entry=lambda x=log_entry: x))

    def on_lcc(self, evt):
        lcc_frame = evt.frame
        if lcc_frame and hasattr(lcc_frame, 'type'):
            def get_log_entry(x=lcc_frame, sent_by_us=evt.sent_by_us):
                res = self.lcc.frame_to_human_readable(x)
                if sent_by_us: res += " (this node)"
                return res
            wx.PostEvent(self.lcc_viewer, LogEntryEvent(get_log_entry=get_log_entry))
            if not evt.sent_by_us:
                wx.PostEvent(self.lcc_nodes, evt)
                if lcc_frame.type == "ProducerConsumerReport":
                    js = f"LCC.dispatchEvent(new CustomEvent('raw-event', {{detail: '{lcc_frame.inner.inner.inner.event_id}'}}));"
                    self.browser.RunScriptAsync(js);

    def view_can_traffic(self, evt):
        self.can_viewer.Show(evt.IsChecked())

    def on_can_viewer_close(self, evt):
        self.menu.view_can_traffic.Check(False)
        self.can_viewer.Hide()

    def view_lcc_traffic(self, evt):
        self.lcc_viewer.Show(evt.IsChecked())

    def on_lcc_viewer_close(self, evt):
        self.menu.view_lcc_traffic.Check(False)
        self.lcc_viewer.Hide()

    def on_lcc_nodes_close(self, evt):
        self.menu.view_lcc_nodes.Check(False)
        self.lcc_nodes.Hide()

    def view_lcc_nodes(self, evt):
        self.lcc_nodes.Show(evt.IsChecked())

    def show_settings_dialog(self, evt):
        global settings
        dialog = SettingsDialog(self, settings)
        if dialog.ShowModal() == wx.ID_CANCEL: return
        settings |= dialog.get_settings()
        settings.save()
        self.lcc.update_node_id(settings["node_id"])

    def on_init(self):
        global settings
        settings.load()

        if "width" in settings:
            self.SetSize((settings['width'], settings['height']))

        self.browser.LoadURL(settings["html_path"])

        self.lcc.update_node_id(settings["node_id"])

        if settings.get("auto_connect"):
            can_driver_name = settings.get("can_driver")
            can_driver_params = settings.get("can_driver_params")
            if can_driver_name and can_driver_params:
                CanDriver = lcc_browser.can.can_drivers.get(can_driver_name)
                if CanDriver is None:
                    print(f"Driver {can_driver_name} not found")
                    settings.pop("can_driver", None)
                else:
                    connection = CanDriver(self.lcc)
                    self.connect(connection, can_driver_params)

    def on_resize(self, evt):
        global settings
        size = evt.GetSize()
        settings["width"] = size[0]
        settings["height"] = size[1]
        evt.Skip()

class LccBrowserApp(wx.App):
    def OnInit(self):
        self.frame = GuiFrame()
        self.SetTopWindow(self.frame)
        self.frame.on_init()
        self.frame.Show()
        return True

def start_gui():
    app = LccBrowserApp()
    app.MainLoop()

if __name__ == "__main__":
    start_gui()
