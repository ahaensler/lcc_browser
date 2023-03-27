import wx
import asyncio
import traceback
from lcc_browser.templates.lcc_nodes_viewer import *
from threading import Thread, Timer
from collections import defaultdict
from lxml import etree
from lcc_browser.xml_to_dict import etree_to_dict
from lcc_browser.wx_controls.lcc_cdi_generator import SegmentGenerator, generate_acdi_panel
from lcc_browser.cdi_registry import CdiRegistry
from lcc_browser.wx_events import *


class LccNodesViewer(LccNodesViewerTemplate):
    query_interval = 5

    def __init__(self, parent):
        super().__init__(parent)
        self.lcc = parent.lcc
        self.Bind(wx.EVT_SHOW, self.on_show)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy)
        self.Bind(EVT_LCC, self.on_lcc)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_node_selected)
        self.button_refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
        self.refresh_timer = Timer(0, lambda: None)
        self.node_id_list = set()
        self.node_id_reported = set()
        self.node_info = defaultdict(dict) # node id to info
        self.node_alias = None # selected node alias

        # this window only lets one async future run at the same time
        # older ones are canceled
        self.future = None
        self.cancel_future = lambda: None
        self.statusbar = self.CreateStatusBar(1, wx.STB_DEFAULT_STYLE)
        self.selected_node_id = None
        self.cdi_registry = None

    def on_show(self, evt):
        if evt.IsShown():
            self.query_nodes()
            self.node_alias = 0x581
        else:
            self.refresh_timer.cancel()
            self.cancel_future()
            # reset forms
            self.node_info = defaultdict(dict)
            self.node_id_list = set()
            self.node_id_reported = set()
            self.node_list.DeleteAllItems()
            self.node_info_text.SetValue("")
            for i in range(1, self.notebook.GetPageCount()):
                self.notebook.DeletePage(1)

    def on_destroy(self, evt):
        self.cancel_future()
        self.refresh_timer.cancel()


    def query_nodes(self):
        self.refresh_timer.cancel()
        self.refresh_timer = Timer(self.query_interval, self.query_nodes)
        self.refresh_timer.start()
        if self.future and not self.future.done():
            # don't confuse nodes by sending messages from multiple threads
            return

        # remove nodes that have timed out from list view
        i = 0
        while i < self.node_list.GetItemCount():
            node_id = self.node_list.GetItem(i, 1).GetText()
            if node_id not in self.node_id_reported:
                self.node_list.DeleteItem(i)
                self.node_id_list.remove(node_id)
            else:
                i += 1

        self.node_id_reported = set()
        self.lcc.send_mti_frame("VerifyNodeIdGlobal")

    async def download_node_details(self, node_id, node_alias):
        selected_node_alias = self.lcc.node_id_to_alias.get(self.selected_node_id)
        is_selected = node_alias == selected_node_alias
        try:
            protocols = await self.lcc.protocol_support_inquiry(node_alias)

            wx.CallAfter(self.refresh_node_list)
            if is_selected:
                wx.CallAfter(self.refresh_node_info_text)

            has_sni = False
            self.node_info[node_id]["protocols"] = ""
            for name, value in protocols.items():
                if name == "_io": continue
                if value:
                    self.node_info[node_id]["protocols"] += f"  {name}\n"
                    if name == "SimpleNodeInformationProtocol":
                        has_sni = True
            if not has_sni: return

            node_information = await self.lcc.simple_node_information(node_alias)
            self.node_info[node_id] |= dict(node_information.fixed_fields)
            self.node_info[node_id] |= dict(node_information.user_fields)
            wx.CallAfter(self.refresh_node_list)
            if is_selected:
                wx.CallAfter(self.refresh_node_info_text)
        except Exception as e:
            print(e)
            print(traceback.format_exc())


    def on_lcc(self, evt):
        if not self.IsShown(): return
        if evt.frame.type == "VerifiedNodeId":
            node_id = evt.frame.inner.inner.inner.node_id
            self.node_id_reported.add(node_id)
            if node_id not in self.node_id_list:
                self.node_list.Append(("Node", node_id))
                self.node_id_list.add(node_id)
            if "protocols" not in self.node_info[node_id]:
                self.lcc.run_future(self.download_node_details(node_id, evt.frame.source_alias))

    async def read_cdi(self, node_alias):
        wx.CallAfter(self.statusbar.SetStatusText, "Reading node config")
        def progress_callback(n):
            wx.CallAfter(self.statusbar.SetStatusText, f"Reading node config {n}")
        try:
            options = await self.lcc.read_memory_options(node_alias)
            # TODO: support more restrictive node read/write alignment
            # not sure if there are LCC devices out there that need aligned io
            is_node_supported = options.write_lengths.arbitrary and \
                options.available_commands.unaligned_write and \
                options.available_commands.unaligned_read
            if not is_node_supported:
                wx.CallAfter(self.statusbar.SetStatusText, "Error: Unsupported node configuration")
                return
            cdi = await self.lcc.read_cdi(node_alias, progress_callback)
        except Exception as e:
            print("Error while reading CDI", type(e), e)
            wx.CallAfter(self.statusbar.SetStatusText, str(e))
            return
        if cdi:
            wx.CallAfter(self.show_cdi, cdi)

    def show_cdi(self, cdi):
        for i in range(1, self.notebook.GetPageCount()):
            self.notebook.DeletePage(1)

        try:
            cdi = etree.fromstring(cdi)
        except Exception as e:
            self.statusbar.SetStatusText("Error while parsing CDI XML data. Try again")
            return

        # load CDI
        update_status = lambda status: wx.CallAfter(self.statusbar.SetStatusText, status)
        self.cdi_registry = CdiRegistry(self.lcc, self.node_alias, update_status)

        acdi = None
        for element in list(cdi):
            if element.tag == "identification":
                identification = etree_to_dict(element).get("identification")
                for tag, element in identification.items():
                    print(tag, element)
            elif element.tag == "acdi":
                acdi = element
            elif element.tag == "segment":
                sg = SegmentGenerator(element, self.notebook, self.cdi_registry)
                panel = sg.get_panel()
                if panel:
                    self.notebook.AddPage(panel, sg.get_name())
        if not acdi is None:
            panel = generate_acdi_panel(element, self.notebook, self.cdi_registry)
            self.notebook.AddPage(panel, "ID")

        self.future, self.cancel_future = self.lcc.run_future(self.refresh_memory())
            
    # load memory values from node
    async def refresh_memory(self):
        if self.cdi_registry is None: return
        try:
            for i, entry in enumerate(self.cdi_registry.entries):
                progress = f"({i}/{len(self.cdi_registry.entries)})"
                wx.CallAfter(self.statusbar.SetStatusText, f"Reading value {entry.name} {progress}")
                await self.cdi_registry.read_memory_async(entry)
                await asyncio.sleep(.001) # some delay makes some slow nodes behave less buggy
            wx.CallAfter(self.statusbar.SetStatusText, "Done")
        except Exception as e:
            print(e)

    def on_refresh(self, evt):
        self.future, self.cancel_future = self.lcc.run_future(self.refresh_memory())

    def on_node_selected(self, evt):
        i = self.node_list.GetNextSelected(-1)
        if i == -1: return
        node_id = self.node_list.GetItem(i, 1).GetText()
        self.selected_node_id = node_id

        self.node_alias = self.lcc.node_id_to_alias.get(node_id)
        protocols = self.node_info[node_id].get("protocols")
        if protocols is None:
            print("Error: Node didn't send protocol support yet.")
            return
        if "ConfigurationDescriptionInformation" in protocols:
            self.cancel_future()
            async_func = self.read_cdi(self.node_alias)
            self.future, self.cancel_future = self.lcc.run_future(async_func)
        self.refresh_node_info_text()

    def refresh_node_list(self):
        for i in range(self.node_list.GetItemCount()):
            node_id = self.node_list.GetItem(i, 1).GetText()
            info = self.node_info[node_id]
            if info.get("manufacturer_name"):
                # display a human-friendly node name
                manufacturer_name = info['manufacturer_name']
                model_name = info['model_name']
                node_name = info['node_name']
                node_name = f"{manufacturer_name} {model_name} {node_name}"
                self.node_list.SetItemText(i, node_name)

    def refresh_node_info_text(self):
        node_id = self.selected_node_id
        info = self.node_info.get(node_id)
        text = \
f"""Node ID {node_id}
Node Alias {self.node_alias}
{info.get("manufacturer_name")} {info.get("model_name")}
Hardware version {info.get("hardware_version")}
Software version {info.get("software_version")}
Node name {info.get("node_name")}
Node description {info.get("node_description")}
Supported Protocols:
{info.get("protocols")}
"""
        self.node_info_text.SetValue(text)
