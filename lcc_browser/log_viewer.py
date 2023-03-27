from lcc_browser.templates.log_viewer import LogViewerTemplate
import wx
import lcc_browser.can
import wx.lib.newevent

LogEntryEvent, EVT_LOG_ENTRY = wx.lib.newevent.NewEvent()

class LogViewer(LogViewerTemplate):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.SetTitle(title)
        self.Bind(EVT_LOG_ENTRY, self.on_log_entry)
        # set monospace font
        font = wx.Font(wx.FontInfo().Family(wx.FONTFAMILY_MODERN))
        self.log_text.SetDefaultStyle(wx.TextAttr(wx.NullColour, font=font))
        self.num_entries = 0
        self.max_entries = 200
            
    def on_log_entry(self, evt):
        if self.IsShown():
            self.num_entries += 1
            log_entry = evt.get_log_entry()
            self.log_text.AppendText(log_entry+'\n')
            if self.num_entries > self.max_entries:
                # rotate log if it gets too long
                val = self.log_text.GetValue()
                idx = 0
                for i in range(5):
                    idx = val.index('\n', idx)+1
                self.num_entries -= 5
                self.log_text.SetValue(val[idx:])
