import traceback

class CdiEntry:
    # linked list of hierarchical CDI groups & fields
    def __init__(self, registry, name, space, offset, size=0, parent=None, window=None):
        self.space = space
        self.offset = offset # this is an absolute address for root, and for other entries an offset relative to parent
        self.size = size # field size for leaves or group / size of a single replication of group
        self.window = window # data entry control for value, or replication entry control in case of group
        self.parent = parent # None if this is root
        self.child_count = 0 # used to calculate hieararchical headings
        self.children = []
        self.name = name
        self.registry = registry

    def get_address(self):
        # of first replication
        address = 0
        group = self.parent
        while group:
            if group.window:
                replication_idx = group.window.GetValue()
                if replication_idx is None: return
                replication_idx = int(replication_idx)
            else:
                replication_idx = 0
            address += group.offset + replication_idx * group.size
            group = group.parent 
        return address + self.offset

    def read(self):
        self.registry.read_memory(self)

    def write(self, value):
        self.registry.write_memory(self, value)

class CdiRegistry:
    def __init__(self, lcc, node_alias, status_callback=None):
        self.entries = []
        self.lcc = lcc
        self.node_alias = node_alias
        self.set_status = lambda: None
        if status_callback: self.set_status = status_callback

        # used during parsing
        root = CdiEntry(self, "Root", 0, 0) # dummy element
        self.current_groups = [root]


    def begin_group(self, offset, space):
        parent = self.current_group()
        name = self.current_heading()
        parent.child_count += 1
        if space is None: space = self.current_space()

        if space == parent.space:
            # group element
            if offset: parent.size += offset
            offset_in_group = self.current_groups[-1].size
        else:
            # segment root element
            offset_in_group = offset

        entry = CdiEntry(self, name, space, offset_in_group, parent=parent)
        self.current_groups.append(entry)
        parent.children.append(entry)
    
    def end_group(self, replication):
        if replication is None: replication = 1
        group = self.current_groups[-1]
        if group.child_count == 0:
            # remove empty group from numbering system
            self.current_groups[-2].child_count -= 1
            self.current_groups[-2].children.pop()
        self.current_groups[-2].size += group.size * replication
        self.current_groups.pop()

    def level(self):
        return len(self.current_groups) - 1

    def parent_heading(self):
        parents = self.current_groups[:-1]
        numbers = [x.child_count for x in parents]
        return ".".join([str(x) for x in numbers])

    def next_heading(self):
        parents = self.current_groups
        numbers = [x.child_count for x in parents]
        numbers[-1] += 1
        return ".".join([str(x) for x in numbers])

    def current_heading(self):
        parents = self.current_groups
        numbers = [x.child_count for x in parents]
        return ".".join([str(x) for x in numbers])

    def current_group(self):
        return self.current_groups[-1]

    def current_space(self):
        return self.current_groups[-1].space

    def current_offset(self):
        return self.current_groups[-1].size

    def add_leaf(self, offset, size, ctrl=None, name=None):
        # both offset and size affect group size
        if offset: self.current_groups[-1].size += offset
        offset_in_group = self.current_groups[-1].size
        if size: self.current_groups[-1].size += size

        parent = self.current_groups[-1]
        if name is None:
            name = self.next_heading()
        parent.child_count += 1
        entry = CdiEntry(self, name, self.current_space(), offset_in_group, size, parent, ctrl)
        self.entries.append(entry)
        parent.children.append(entry)
        return entry

    async def read_memory_async(self, entry):
        try:
            result = await self.lcc.read_memory_configuration(self.node_alias, entry.space, entry.get_address(), entry.size)
            if len(result) != entry.size:
                print(f"Error: Node returned invalid data for field {entry.name} (actual size {len(result)}, expected {entry.size})")
            entry.window.set_raw_value(result)
            return result
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.set_status(str(e))

    def read_memory(self, entry):
        async_func = self.read_memory_async(entry)
        future, cancel_future = self.lcc.run_future(async_func)

    async def write_memory_async(self, entry, data):
        try:
            await self.lcc.write_memory_configuration(self.node_alias, entry.space, entry.get_address(), data)
            entry.window.set_raw_value(data)
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.set_status(str(e))

    def write_memory(self, entry, data):
        async_func = self.write_memory_async(entry, data)
        self.lcc.run_future(async_func)

    async def read_group_memory_async(self, entry):
        # traverse group tree and read currently selected memory
        children = [*entry.children]
        while child := children.pop():
            children += child.children
            if child.child_count == 0:
                # it's a leaf
                await self.read_memory_async(child)

    def read_group_memory(self, entry):
        async_func = self.read_group_memory_async(entry)
        self.future, self.cancel_future = self.lcc.run_future(async_func)
