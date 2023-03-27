# -*- coding: UTF-8 -*-
#
# generated by wxGlade 1.0.4 on Tue Mar 21 02:50:02 2023
#

import wx

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode
# end wxGlade


class LogViewerTemplate(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: LogViewerTemplate.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((400, 300))
        self.SetTitle("Log Viewer")

        self.panel_1 = wx.Panel(self, wx.ID_ANY)

        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        self.log_text = wx.TextCtrl(self.panel_1, wx.ID_ANY, "", style=wx.TE_DONTWRAP | wx.TE_MULTILINE | wx.TE_READONLY)
        sizer_1.Add(self.log_text, 1, wx.EXPAND, 0)

        self.panel_1.SetSizer(sizer_1)

        self.Layout()
        # end wxGlade

# end of class LogViewerTemplate
