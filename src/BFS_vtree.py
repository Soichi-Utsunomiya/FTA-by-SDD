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
    visited_event = set()
    elim_DAG = {}

    while queue:
        event = queue.popleft()
        visited_event.add(event)
        if event in gate_map:
            print(event,gate_map[event].children)
            elim_DAG[event] = []
            for child_event in gate_map[event].children:
                if child_event not in visited_event:
                    queue.append(child_event)
                    order_event.append(child_event)
                    elim_DAG[event].append(child_event)
                    visited_event.add(child_event)

    child_num = {}
    for event in reversed(order_event):
        if event in elim_DAG:
            valid_event = []
            for child_event in elim_DAG[event]:
                if child_num[child_event] == 1:
                    valid_event.append(child_event)
            if len(valid_event) > 0:
                v_map[event] = build_subTree(valid_event)
                child_num[event] = 1
            else:
                child_num[event] = 0

        elif event not in elim_DAG:
            child_num[event] = 1
            custum_vtree.append("L " + str(event_count) + " " + str(var_map[event]))
            v_map[event] = event_count
            event_count += 1

    top = []
    top.append("vtree " + str(event_count))
    custum_vtree = top + custum_vtree

    with open(vtree_file, "w") as out:
        for row in custum_vtree:
            print(row, file = out)