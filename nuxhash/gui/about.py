import os
from pathlib import Path

import wx
from wx.lib.agw.hyperlink import HyperLinkCtrl

from nuxhash.version import __copyright__, __version__


WEBSITE = 'https://github.com/YoRyan/nuxhash'
LICENSE = 'https://www.gnu.org/licenses/gpl-3.0.html'

LOGO_PATH = Path(os.path.dirname(__file__))/'icons'/'nuxhash_128x128.png'


class AboutScreen(wx.Panel):

    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        h_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        self.SetSizer(h_sizer)
        v_sizer = wx.BoxSizer(orient=wx.VERTICAL)
        h_sizer.Add(v_sizer, wx.SizerFlags().Proportion(1)
                                            .Align(wx.ALIGN_CENTER))

        with open(LOGO_PATH, 'rb') as f:
            logo = wx.Image(f, type=wx.BITMAP_TYPE_PNG)
        v_sizer.Add(wx.StaticBitmap(self, bitmap=wx.Bitmap(logo)),
                    wx.SizerFlags().Align(wx.ALIGN_CENTER))

        v_sizer.AddSpacer(15)

        appName = wx.StaticText(
                self, label=f'nuxhash {__version__}', style=wx.ALIGN_CENTER)
        appName.SetFont(self.GetFont().Scale(2.0))
        v_sizer.Add(appName, wx.SizerFlags().Expand())

        v_sizer.AddSpacer(15)

        v_sizer.Add(wx.StaticText(self, label='A NiceHash client for Linux.',
                                  style=wx.ALIGN_CENTER),
                    wx.SizerFlags().Expand())

        v_sizer.AddSpacer(15)

        copyright = wx.StaticText(self, label=__copyright__, style=wx.ALIGN_CENTER)
        copyright.SetFont(self.GetFont().Scale(0.8))
        v_sizer.Add(copyright, wx.SizerFlags().Expand())

        v_sizer.AddSpacer(30)

        links = wx.BoxSizer(orient=wx.HORIZONTAL)
        links.Add(HyperLinkCtrl(self, label='Website', URL=WEBSITE))
        links.AddSpacer(30)
        links.Add(HyperLinkCtrl(self, label='License', URL=LICENSE))
        v_sizer.Add(links, wx.SizerFlags().Align(wx.ALIGN_CENTER))

