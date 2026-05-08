import xml.etree.ElementTree as ET
from FT_to_dnf import gate_child_map, gate_grandchild_map, prob_map
import math

var_map = {}
child_map = {}
name_prob_map = []
visited_var = []
custum_vtree = []
stack = []
event_count = 0
event_list = []

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

def BFS(event_elem):
    global event_list, child_map
    gate = event_elem.get("gate")
    id = event_elem.get("id")

    if gate:
        child_events = event_elem.findall("event")
        gate_events = []
        for child_event in child_events:
            child_gate = child_event.get("gate")
            child_id = child_event.get("id")

            if child_gate:
                gate_events.append(child_event)
            elif child_id not in child_map:
                child_map[id].append(child_id)
            child_map[child_id] = []
        for gate_event in gate_events:
            child_id = gate_event.get("id")
            child_map[id].append(child_id)
            event_list.append(gate_event)

def BFS_vtree(xml_path, pyeda_expr, vtree_file):
    global var_map, visited_var, custum_vtree, event_list, name_prob_map, event_count, stack, child_map
    event_count = 0
    var_map.clear()
    visited_var.clear()
    custum_vtree.clear()
    event_list.clear()
    name_prob_map.clear()
    stack.clear()
    child_map.clear()
    support_vars = sorted([str(v) for v in pyeda_expr.support])

    i = 1
    for var in support_vars:
        var_map[var] = i
        name_prob_map.append(prob_map[var])
        visited_var.append(0)
        i += 1
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    root_id = root.get("id")

    event_list.append(root)
    child_map[root_id] = []

    for event in event_list:
        BFS(event)

    for parent_name, children in reversed(child_map.items()):
        if len(children) > 0:

            print(parent_name,children)

            var_map[parent_name] = build_subTree(children)

            print(parent_name, var_map[parent_name])

    top = []
    top.append("vtree " + str(event_count))
    custum_vtree = top + custum_vtree

    with open(vtree_file, "w") as out:
        for row in custum_vtree:
            print(row, file = out)