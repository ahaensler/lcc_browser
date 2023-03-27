""" Generates wx panels from a CDI XML elements."""
import wx
import wx.lib.scrolledpanel
from lcc_browser.xml_to_dict import etree_to_dict
from lcc_browser.wx_controls.event_id_input import EventIdInput
from lcc_browser.wx_controls.map_input import MapControl, MapInput
from lcc_browser.wx_controls.entry_heading import EntryHeading
from lcc_browser.wx_controls.int_input import IntInput
from lcc_browser.wx_controls.string_input import StringInput

def get_integer(d, name):
    res = d.get(name)
    if res is not None:
        try:
            res = int(res)
        except:
            print(f"Could not convert {res} to integer.")
            res = None
    return res

class SegmentGenerator:
    def __init__(self, segment_xml, parent, registry):
        # parses <group> or <segment> xml elements
        # generates a wx UI
        # and populates a registry of the node's memory locations

        self.parent = parent
        self.registry = registry
        level = registry.level()

        self.name = None
        self.description = None
        self.has_name = False

        # parse attributes
        space = get_integer(segment_xml.attrib, "space")
        origin = get_integer(segment_xml.attrib, "origin")
        if space is not None and origin is None: origin = 0
        offset = get_integer(segment_xml.attrib, "offset")
        self.replication = get_integer(segment_xml.attrib, "replication")
        self.repnames = []
        if self.replication == 0:
            print("CDI replication is set to 0. Ignoring this section.")
            return
        registry.begin_group(offset, space)
        if origin is not None: registry.current_group().offset = origin

        children = list(segment_xml)
        if len(children) == 0:
            self.panel = None
            registry.end_group(self.replication)
            return

        if level == 0:
            self.panel = wx.lib.scrolledpanel.ScrolledPanel(parent, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.HSCROLL | wx.VSCROLL)
            self.panel.SetScrollRate(5, 5)
        else:
            self.panel = wx.Panel(parent)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        for element in children:
            tag = element.tag
            if tag == "name":
                self.name = element.text
            elif tag == "description":
                self.description = element.text
            elif tag == "repname":
                self.repnames.append(element.text)
            elif tag == "group":
                self.ensure_heading()
                sg  = SegmentGenerator(element, self.panel, registry)
                panel = sg.get_panel()
                if panel:
                    # only add groups with content
                    self.sizer.Add(panel, border=5 * (level+1), flag=wx.LEFT)
            elif tag == "string":
                self.ensure_heading()
                element = etree_to_dict(element)['string']
                offset = get_integer(element, "@offset")
                size = get_integer(element, "@size")
                map = element.get("map")
                assert size
                entry = registry.add_leaf(offset, size)
                if map:
                    relations = map["relation"]
                    if type(relations) != list: relations = [relations]
                    choices = {x.get("property"): x.get("value") for x in relations}
                    ctrl = MapInput(self.panel, choices, entry, None, str)
                else:
                    ctrl = StringInput(self.panel, entry.size)
                ctrl.cdi_entry = entry
                entry.window = ctrl
                self.add_name_and_description(element)
                self.sizer.Add(ctrl, border=5 * (level+2), flag=wx.LEFT)
            elif tag == "int":
                self.ensure_heading()
                element = etree_to_dict(element)['int']
                min = get_integer(element, "min")
                max = get_integer(element, "max")
                default = get_integer(element, "default")
                map = element.get("map")
                offset = get_integer(element, "@offset")
                size = get_integer(element, "@size")
                assert size
                if map:
                    relations = map["relation"]
                    if type(relations) != list: relations = [relations]
                    choices = {x.get("property"): x.get("value") for x in relations}
                    ctrl = MapInput(self.panel, choices, None, default, int)
                else:
                    ctrl = IntInput(self.panel, min, max, default)

                entry = registry.add_leaf(offset, size, ctrl)
                ctrl.cdi_entry = entry
                self.add_name_and_description(element)
                self.sizer.Add(ctrl, border=5 * (level+2), flag=wx.LEFT)
            elif tag == "eventid":
                self.ensure_heading()
                element = etree_to_dict(element)['eventid']
                ctrl = EventIdInput(self.panel)
                offset = get_integer(element, "@offset")
                entry = registry.add_leaf(offset, 8, ctrl)
                ctrl.cdi_entry = entry
                self.add_name_and_description(element)
                self.sizer.Add(ctrl, border=5 * (level+2), flag=wx.LEFT)

        self.ensure_heading()

        registry.end_group(self.replication)

        self.panel.SetSizer(self.sizer)
        self.panel.Layout()
        self.panel.FitInside()
        #border_sizer.Fit(self.panel)


    def ensure_heading(self):
        # add heading name and replication field
        if self.registry.level == 0: return
        if self.has_name: return
        self.has_name = True

        label = wx.StaticText(self.panel, wx.ID_ANY)
        heading = self.registry.parent_heading()
        if self.name:
            heading += " " + self.name
        label.SetLabelMarkup(f"<b>{heading}</b>")
        label.Wrap(700)
        sizer2 = wx.BoxSizer(wx.VERTICAL)
        sizer2.Add(label, border=5 * self.registry.level(), flag=wx.LEFT)
        self.sizer.Add(sizer2, border=5, flag=wx.TOP) # vertical space

        # description
        if self.description:
            label = wx.StaticText(self.panel, wx.ID_ANY, self.description)
            label.Wrap(700)
            self.sizer.Add(label, border=5 * (self.registry.level()+1), flag=wx.LEFT)

        # replication field
        if not self.replication is None:
            if len(self.repnames) == self.replication + 1:
                # make it a choice
                label = f"Select affected instance ({self.repnames[0]}) for section {self.registry.parent_heading()}."
                choices = {i: f"{i+1} {x}" for i, x in enumerate(self.repnames[1:])}
                ctrl = MapControl(self.panel, choices)
                ctrl.SetValue(0)
                ctrl.Bind(wx.EVT_CHOICE, lambda evt, group=self.registry.current_group(): self.read_replication(group))
            elif len(self.repnames) == self.replication:
                # make it a choice
                label = f"Select affected instance for section {self.registry.parent_heading()}."
                choices = {i: f"{i+1} {x}" for i, x in enumerate(self.repnames)}
                ctrl = MapControl(self.panel, choices)
                ctrl.SetValue(0)
                ctrl.Bind(wx.EVT_CHOICE, lambda evt, group=self.registry.current_group(): self.read_replication(group))
            elif len(self.repnames) == 1:
                # make it a single label
                label = f"Section {self.registry.parent_heading()} affects multiple instances ({self.repnames[0]}). Enter a number from 1 to {self.replication}."
                ctrl = wx.SpinCtrl(self.panel, wx.ID_ANY, value="1", min=1, max=self.replication)
                ctrl.SetValue(0)
                ctrl.Bind(wx.EVT_SPINCTRL, lambda evt, group=self.registry.current_group(): self.read_replication(group))
            elif len(self.repnames) == 0:
                # no repmane label(s) available
                label = f"Section {self.registry.parent_heading()} affects multiple instances. Enter an instance number from 1 to {self.replication}."
                ctrl = wx.SpinCtrl(self.panel, wx.ID_ANY, value="1", min=1, max=self.replication)
                ctrl.SetValue(0)
                ctrl.Bind(wx.EVT_SPINCTRL, lambda evt, group=self.registry.current_group(): self.read_replication(group))
            else:
                # unsupported repname mapping
                print(f"CDI has unsupported repname label(s) in section {self.registry.parent_heading()}: {self.repnames}")
                print(len(self.repnames), self.replication)
                print(len(self.repnames) == self.replication + 1)
            if ctrl:
                label = wx.StaticText(self.panel, wx.ID_ANY, label)
                self.sizer.Add(label, border=5 * (self.registry.level()+1), flag=wx.LEFT)
                self.sizer.Add(ctrl, border=5 * (self.registry.level()+1), flag=wx.LEFT)
                self.registry.current_group().window = ctrl

    def read_replication(self, group):
        self.registry.read_group_memory(group)

    def add_name_and_description(self, element):
        field_name = element.get("name")
        description = element.get("description")
        field_name = f"{self.registry.current_heading()} {field_name}"
        entry = self.registry.entries[-1]
        if field_name:
            label = EntryHeading(self.panel, field_name, entry)
            sizer2 = wx.BoxSizer(wx.VERTICAL)
            sizer2.Add(label, border=5 * (self.registry.level()+1), flag=wx.LEFT)
            self.sizer.Add(sizer2, border=5, flag=wx.TOP) # vertical space
        if description:
            label = wx.StaticText(self.panel, wx.ID_ANY, description)
            label.Wrap(700)
            self.sizer.Add(label, border=5 * (self.registry.level()+1), flag=wx.LEFT)

    def get_panel(self):
        return self.panel

    def get_name(self):
        return self.name if self.name else "No Name"

    
def generate_acdi_panel(element, parent, registry):
    panel = wx.lib.scrolledpanel.ScrolledPanel(parent, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.HSCROLL | wx.VSCROLL)
    panel.SetScrollRate(5, 5)
    sizer = wx.BoxSizer(wx.VERTICAL)

    def add_field(name, ctrl, address, size):
        nonlocal panel, sizer
        label = wx.StaticText(panel, wx.ID_ANY, name)
        sizer.Add(label, border=5, flag=wx.LEFT)
        entry = registry.add_leaf(address, size, ctrl, name)
        entry.window = ctrl
        ctrl.cdi_entry = entry
        sizer.Add(ctrl, border=5, flag=wx.LEFT)

    fixed = element.attrib.get("fixed")
    if fixed is None or fixed >= 4:
        registry.begin_group(0, 252)
        add_field("Version of fixed fields", IntInput(panel, None, None, None), 0, 1)
        add_field("Manufacturer", StringInput(panel, 41), 0, 41)
        add_field("Model", StringInput(panel, 41), 0, 41)
        add_field("Hardware version", StringInput(panel, 21), 0, 21)
        add_field("Software version", StringInput(panel, 21), 0, 21)
        registry.end_group(None)

    var = element.attrib.get("var")
    if var is None or var >= 2:
        registry.begin_group(0, 251)
        add_field("Version of variable fields", IntInput(panel, None, None, None), 0, 1)
        add_field("User-supplied name", StringInput(panel, 63), 0, 63)
        add_field("User-supplied description", StringInput(panel, 64), 0, 64)
        registry.end_group(None)

    panel.SetSizer(sizer)
    panel.Layout()
    panel.FitInside()
    return panel
