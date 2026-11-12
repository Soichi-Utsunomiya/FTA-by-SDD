from collections import deque
import tempfile
import os


def DFS_vtree(top_gate, var_map, gate_map):

    global custum_vtree, event_count
    event_count = 0
    custum_vtree = []
    v_map = {}

    order_event = [top_gate]
    visited_event = set()
    elim_DAG = {}
    basic_parents = {}
    gate_children = {}

    def build_subTree(children):
        global event_count

        if len(children) == 1:
            return v_map[children[0]]

        mid = len(children) // 2
        left = build_subTree(children[:mid])
        right = build_subTree(children[mid:])

        custum_vtree.append("I " + str(event_count) + " " + str(left) + " " + str(right))
        event_count += 1
        return event_count - 1

    def Counter(event):
        if event in gate_children:
            return gate_children[event]
        gate_children[event] = []
        for child_event in gate_map[event].children:
            if child_event[0] == '~':
                child_event = child_event.removeprefix('~')
            if child_event not in gate_map:
                if child_event not in basic_parents:
                    basic_parents[child_event] = []
                basic_parents[child_event].append(event)
                gate_children[event].append(child_event)
            else:  
                gate_children[event] += Counter(child_event)
        return gate_children[event]

    Counter(top_gate)
    print(basic_parents)

    sorted_children = {}
    for g,c in gate_map.items():
        basic_events = list((set(c.children) & set(basic_parents)))
        sorted_basic_events = sorted(
            basic_events,
            key = lambda child: (
                -len(basic_parents[child.removeprefix("~")]),
                child.removeprefix("~")
            )
        )
        gate_events =list(set(c.children) - set(basic_events))
        sorted_gate_events = sorted(
            gate_events,
            key = lambda child: (
                len(gate_children[child.removeprefix("~")]),
                child.removeprefix("~")
            )   
        )
        sorted_children[g] = sorted_basic_events + sorted_gate_events
        print(sorted_children[g])

    order_event = [top_gate]
    visited_event = set()

    def DFS(event):
        visited_event.add(event)
        if event in gate_map:
            elim_DAG[event] = []
            for child_event in sorted_children[event]:
                if child_event[0] == '~':
                    child_event = child_event.removeprefix('~')
                if child_event not in visited_event:
                    order_event.append(child_event)
                    elim_DAG[event].append(child_event)
                    visited_event.add(child_event)
                    DFS(child_event)

    DFS(top_gate)

    child_num = {}
    var_order = deque()

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
        else:
            child_num[event] = 1
            custum_vtree.append("L " + str(event_count) + " " + str(var_map[event]))
            v_map[event] = event_count
            event_count += 1
            var_order.appendleft(event)

    print(f"Order:{list(var_order)}")
    lines = ["vtree " + str(event_count)] + custum_vtree
    #print(lines)
    return "\n".join(lines).encode()


def DFS_vtree_to_tempfile(top_gate, var_map, gate_map):
    """
    vtreeのバイト列を一時ファイルに書き出し、
    そのパスを返す。呼び出し元で削除すること。
    """
    vtree_bytes = DFS_vtree(top_gate, var_map, gate_map)
    tmp = tempfile.NamedTemporaryFile(
        mode='wb', suffix='.vtree', delete=False
    )
    tmp.write(vtree_bytes)
    tmp.close()
    return tmp.name
