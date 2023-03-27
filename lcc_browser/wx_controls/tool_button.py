import wx

class ToolButton(wx.Button):
    def __init__(self, parent, art_id, label=""):
        super().__init__(parent)
        self.SetBitmapLabel(wx.ArtProvider.GetBitmap(art_id, wx.ART_MENU))
        self.SetMinSize((self.GetSize()[1]+2, wx.DefaultCoord))
        self.SetToolTip(wx.ToolTip(label))
