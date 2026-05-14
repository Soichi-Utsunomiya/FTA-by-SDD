import xml.etree.ElementTree as ET
from collections import deque

v_map = {}
child_map = {}
name_prob_map = []
custum_vtree = []
event_count = 0

def build_subTree(children):
    global event_count, v_map, child_map

    if len(children) == 1:
        return v_map[children[0]]

    mid = len(children) // 2
    left = build_subTree(children[:mid])
    right = build_subTree(children[mid:])

    custum_vtree.append("I " + str(event_count) + " " +  str(left) + " " + str(right))
    event_count += 1
    return event_count-1

def BFS_vtree(top_gate, var_map, gate_map, vtree_file):
    global custum_vtree, name_prob_map, event_count, child_map
    event_count = 0
    custum_vtree.clear()
    name_prob_map.clear()
    child_map.clear()

    queue = deque([top_gate])
    order_event = [top_gate]

    while queue:
        event = queue.popleft()
        if event in gate_map and len(gate_map[event].children) > 0:
            for child_event in gate_map[event].children:
                queue.append(child_event)
                order_event.append(child_event)

    for event in reversed(order_event):
        if event in gate_map and len(gate_map[event].children) > 0:
            v_map[event] = build_subTree(gate_map[event].children)
        else:
            custum_vtree.append("L " + str(event_count) + " " + str(var_map[event]))
            v_map[event] = event_count
            event_count += 1

    top = []
    top.append("vtree " + str(event_count))
    custum_vtree = top + custum_vtree

    with open(vtree_file, "w") as out:
        for row in custum_vtree:
            print(row, file = out)