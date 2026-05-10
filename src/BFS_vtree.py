import xml.etree.ElementTree as ET
from FT_to_dnf import prob_map
from collections import deque

var_map = {}
child_map = {}
name_prob_map = []
custum_vtree = []
event_count = 0

def build_subTree(children):
    global event_count, var_map, child_map

    if len(children) == 1:
        if len(child_map[children[0]]) == 0:
            custum_vtree.append("L " + str(event_count) + " " + str(var_map[children[0]]))
            event_count += 1
            return event_count-1
        else:
            return var_map[children[0]]

    mid = len(children) // 2
    left = build_subTree(children[:mid])
    right = build_subTree(children[mid:])

    custum_vtree.append("I " + str(event_count) + " " +  str(left) + " " + str(right))
    event_count += 1
    return event_count-1

def BFS_vtree(xml_path, vtree_file):
    global var_map, custum_vtree, name_prob_map, event_count, child_map
    event_count = 0
    var_map.clear()
    custum_vtree.clear()
    name_prob_map.clear()
    child_map.clear()

    tree = ET.parse(xml_path)
    root = tree.getroot()

    prob_map = {}

    support_vars_set = set()
    for elem in root.iter("event"):
        if elem.get("gate") is None and elem.get("id") is not None:
            support_vars_set.add(elem.get("id"))
            prob_map[elem.get("id")] = elem.get("value")
    support_vars = sorted(list(support_vars_set))

    i = 1
    for var in support_vars:
        var_map[var] = i
        name_prob_map.append(prob_map[var])
        i += 1

    queue = deque([root])
    child_map[root.get("id")] = []

    while queue:
        event = queue.popleft()
        gate = event.get("gate")
        id = event.get("id")

        if gate:
            child_events = event.findall("event")
            for child_event in child_events:
                child_gate = child_event.get("gate")
                child_id = child_event.get("id")
                if id not in child_map:
                    child_map[id] = []
                child_map[id].append(child_id)
                if child_gate:
                    if child_id not in child_map:
                        child_map[child_id] = []
                    queue.append(child_event)
                else:
                    child_map[child_id] = []

    for parent_name, children in reversed(child_map.items()):
        if len(children) > 0:
            var_map[parent_name] = build_subTree(children)

    top = []
    top.append("vtree " + str(event_count))
    custum_vtree = top + custum_vtree

    with open(vtree_file, "w") as out:
        for row in custum_vtree:
            print(row, file = out)