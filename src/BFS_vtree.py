import xml.etree.ElementTree as ET
from FT_to_dnf import gate_child_map, gate_grandchild_map

var_map = {}
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
    global event_count, stack, custum_vtree, alone, event_list
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

def BFS(event_elem):
    global event_list
    gate = event_elem.get("gate")
    id = event_elem.get("id")
    print(id)

    if gate:
        print(gate_grandchild_map[id])
        child_events = event_elem.findall("event")
        score_gate = {}
        for child_event in child_events:
            child_event_id = child_event.get("id")
            print(gate_child_map[child_event_id])
            if child_event_id in gate_child_map:
                #core_gate[child_event_id] = gate_grandchild_map[id] & gate_child_map[child_event_id]
                print(len(gate_grandchild_map[id] & gate_child_map[child_event_id]))
        for child_event in child_events:
            event_list.append(child_event)
    else:
        return id

def BFS_vtree(xml_path, pyeda_expr):
    global var_map, visited_var, custum_vtree, event_list
    support_vars = sorted([str(v) for v in pyeda_expr.support])

    i = 1
    for var in support_vars:
        var_map[var] = i
        visited_var.append(0)
        i += 1
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    event_list.append(root)

    for event in event_list:
        BFS(event)

    top = []
    top.append("vtree " + str(event_count))
    custum_vtree = top + custum_vtree

    with open("input/custom.vtree", "w") as out:
        for row in custum_vtree:
            print(row, file = out)