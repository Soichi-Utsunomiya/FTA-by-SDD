import xml.etree.ElementTree as ET
from FT_to_dnf import gate_child_map, gate_grandchild_map, prob_map
import math

var_map = {}
name_prob_map = []
visited_var = []
custum_vtree = []
stack = []
alone = False
event_count = 0
event_list = []

def synthesis():
    global custum_vtree, stack, event_count
    right = stack.pop()
    left = stack.pop()
    custum_vtree.append("I " + str(event_count) + " " + str(left) + " " + str(right))
    stack.append(str(event_count))
    event_count += 1

def FT_vtree(event_elem):
    global event_count, stack, custum_vtree, alone, event_list, visited_var, var_map
    gate = event_elem.get("gate")
    event_id = event_elem.get("id")

    if gate is None:
        if event_id in var_map and visited_var[var_map[event_id]-1] == 0:
            custum_vtree.append("L " + str(event_count) + " " + str(var_map[event_id]))
            stack.append(str(event_count))
            event_count += 1
            visited_var[var_map[event_id]-1] = 1
            return 1
        else:
            return 0
    
    child_events = event_elem.findall("event")

    if gate:
        valid_event = 0
        common_event = 0
        gate_child_events = []
        for child_event in child_events:
            child_gate = child_event.get("gate")

            if child_gate is None:
                event = FT_vtree(child_event)
                common_event += event
                valid_event += event
                if common_event == 2:
                    synthesis()
                    common_event = 0
                    valid_event -= 1
                    if valid_event == 2:
                        synthesis()
                        valid_event -= 1
            else:
                gate_child_events.append(child_event)
                
        gate_event = valid_event
        for child_event in gate_child_events:
            event = FT_vtree(child_event)
            gate_event += event
            valid_event += event
            if gate_event >= 2:
                synthesis()
                gate_event = 0
                valid_event -= 1
                if valid_event == 2:
                    synthesis()
                    valid_event -= 1
        if valid_event > 1:
            synthesis()
            return 1
        elif valid_event == 1:
            return 1
        else:
            return 0

def DFS_vtree(xml_path, pyeda_expr, vtree_file):
    global var_map, visited_var, custum_vtree, event_list, name_prob_map, event_count, stack, alone
    alone = False
    event_count = 0
    var_map.clear()
    visited_var.clear()
    custum_vtree.clear()
    event_list.clear()
    name_prob_map.clear()
    stack.clear()
    support_vars = sorted([str(v) for v in pyeda_expr.support])

    i = 1
    for var in support_vars:
        var_map[var] = i
        name_prob_map.append(prob_map[var])
        visited_var.append(0)
        i += 1
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    FT_vtree(root)

    top = []
    top.append("vtree " + str(event_count))
    custum_vtree = top + custum_vtree

    with open(vtree_file, "w") as out:
        for row in custum_vtree:
            print(row, file = out)