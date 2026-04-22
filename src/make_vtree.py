import xml.etree.ElementTree as ET
from FT_to_dnf import prob_map
import os

var_map = {}
name_prob_map = []
visited_var = []
custum_vtree = []
stack = []
alone = False
event_count = 0

def synthesis():
    global custum_vtree, stack, event_count
    right = stack.pop()
    left = stack.pop()
    custum_vtree.append("I " + str(event_count) + " " + str(left) + " " + str(right))
    stack.append(str(event_count))
    event_count += 1

def FT_vtree(event_elem):
    global event_count, stack, custum_vtree, alone
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
    
    #child_events = [FT_vtree(child) for child in event_elem.findall("event")]
    child_events = event_elem.findall("event")

    if gate:
        valid_event = 0
        for child_event in child_events:
            valid_event += FT_vtree(child_event)
            if valid_event != 0 and valid_event % 2 == 0:
                synthesis()
                valid_event -= 1
        if valid_event >= 1:
            for i in range(valid_event-1):
                synthesis()
            if alone:
                synthesis()
                alone = False
        if valid_event == 1:
            if alone:
                synthesis()
                alone = False
            else:
                alone = True
                return 0
    return 1

def make_vtree(xml_path, pyeda_expr, vtree_file):
    global var_map, visited_var, custum_vtree, name_prob_map
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