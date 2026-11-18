from collections import deque
import tempfile
import os


def BDD_vtree(top_gate, var_map, gate_map):

    global custum_vtree, event_count
    event_count = 0
    custum_vtree = []
    v_map = {}

    order_event = [top_gate]
    visited_event = set()
    elim_DAG = {}
    basic_parents = {}
    gate_children = {}
    
    def Counter(event):
        if event in gate_children:
            return gate_children[event]
        gate_children[event] = 0
        for child_event in gate_map[event].children:
            if child_event[0] == '~':
                child_event = child_event.removeprefix('~')
            if child_event not in gate_map:
                if child_event not in basic_parents:
                    basic_parents[child_event] = []
                basic_parents[child_event].append(event)
                gate_children[event] += 1
            else:  
                gate_children[event] += Counter(child_event)
        return gate_children[event]

    Counter(top_gate)

    sorted_children = {}
    for g,c in gate_map.items():

        children = [
            child.removeprefix("~")
            for child in c.children
        ]

        basic_events = list((set(children) & set(basic_parents)))
        sorted_basic_events = sorted(
            basic_events,
            key = lambda child: (
                -len(basic_parents[child.removeprefix("~")]),
                child.removeprefix("~")
            )
        )
        gate_events =list(set(children) - set(basic_events))
        sorted_gate_events = sorted(
            gate_events,
            key = lambda child: (
                gate_children[child.removeprefix("~")],
                child.removeprefix("~")
            )   
        )
        sorted_children[g] = sorted_basic_events + sorted_gate_events

    order_event = deque()
    var_order = []
    visited_event = set()

    def DFS(event):
        visited_event.add(event)
        if event in gate_map:
            for child_event in sorted_children[event]:
                if child_event[0] == '~':
                    child_event = child_event.removeprefix('~')
                if child_event not in visited_event:
                    if child_event not in gate_map:
                        order_event.appendleft(child_event)
                        var_order.append(child_event)
                    visited_event.add(child_event)
                    DFS(child_event)
    DFS(top_gate)

    custum_vtree.append("L " + str(event_count) + " " + str(var_map[order_event.popleft()]))
    right = event_count
    event_count += 1
    while order_event:
        event = order_event.popleft()
        custum_vtree.append("L " + str(event_count) + " " + str(var_map[event]))
        left = event_count
        event_count += 1
        custum_vtree.append("I " + str(event_count) + " " + str(left) + " " + str(right))
        right = event_count
        event_count += 1

    print(f"Order:{list(var_order)}")
    lines = ["vtree " + str(event_count)] + custum_vtree
    return "\n".join(lines).encode(), gate_children, basic_parents