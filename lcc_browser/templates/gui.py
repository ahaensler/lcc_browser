#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# generated by wxGlade 1.0.4 on Mon Mar 27 22:52:23 2023
#

import wx

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode
# end wxGlade


class OpenLcbGui(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: OpenLcbGui.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((400, 300))
        self.SetTitle("LCC Browser")

        # Menu Bar
        self.menu = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Establish...", "")
        self.Bind(wx.EVT_MENU, self.establish_connection, item)
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Disconnect", "")
        self.Bind(wx.EVT_MENU, self.disconnect, item)
        self.menu.Append(wxglade_tmp_menu, "&Connection")
        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Reload HTML", "")
        self.Bind(wx.EVT_MENU, self.reload_browser, item)
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Settings...", "")
        self.Bind(wx.EVT_MENU, self.show_settings_dialog, item)
        self.menu.Append(wxglade_tmp_menu, "&Layout")
        wxglade_tmp_menu = wx.Menu()
        self.menu.view_lcc_nodes = wxglade_tmp_menu.Append(wx.ID_ANY, "LCC Nodes", "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.view_lcc_nodes, self.menu.view_lcc_nodes)
        wxglade_tmp_menu.AppendSeparator()
        self.menu.view_can_traffic = wxglade_tmp_menu.Append(wx.ID_ANY, "CAN Traffic", "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.view_can_traffic, self.menu.view_can_traffic)
        self.menu.view_lcc_traffic = wxglade_tmp_menu.Append(wx.ID_ANY, "LCC Traffic", "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.view_lcc_traffic, self.menu.view_lcc_traffic)
        self.menu.Append(wxglade_tmp_menu, "&View")
        self.SetMenuBar(self.menu)
        # Menu Bar end

        self.panel = wx.Panel(self, wx.ID_ANY)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.sizer.Add((0, 0), 0, 0, 0)

        self.panel.SetSizer(self.sizer)

        self.Layout()

        # end wxGlade

    def establish_connection(self, event):  # wxGlade: OpenLcbGui.<event_handler>
        print("Event handler 'establish_connection' not implemented!")
        event.Skip()

    def disconnect(self, event):  # wxGlade: OpenLcbGui.<event_handler>
        print("Event handler 'disconnect' not implemented!")
        event.Skip()

    def reload_browser(self, event):  # wxGlade: OpenLcbGui.<event_handler>
        print("Event handler 'reload_browser' not implemented!")
        event.Skip()

    def show_settings_dialog(self, event):  # wxGlade: OpenLcbGui.<event_handler>
        print("Event handler 'show_settings_dialog' not implemented!")
        event.Skip()

    def view_lcc_nodes(self, event):  # wxGlade: OpenLcbGui.<event_handler>
        print("Event handler 'view_lcc_nodes' not implemented!")
        event.Skip()

    def view_can_traffic(self, event):  # wxGlade: OpenLcbGui.<event_handler>
        print("Event handler 'view_can_traffic' not implemented!")
        event.Skip()

    def view_lcc_traffic(self, event):  # wxGlade: OpenLcbGui.<event_handler>
        print("Event handler 'view_lcc_traffic' not implemented!")
        event.Skip()

# end of class OpenLcbGui

class MyApp(wx.App):
    def OnInit(self):
        self.frame = OpenLcbGui(None, wx.ID_ANY, "")
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True

# end of class MyApp

if __name__ == "__main__":
    app = MyApp(0)
    app.MainLoop()