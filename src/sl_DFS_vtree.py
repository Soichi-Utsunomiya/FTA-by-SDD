from collections import deque
import tempfile
import os

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

    custum_vtree.append("I " + str(event_count) + " " + str(left) + " " + str(right))
    event_count += 1
    return event_count - 1

def DFS_vtree(top_gate, var_map, gate_map):
    """
    FTのBFS走査に基づく平衡木vtreeを構築し、
    PySDDが読み込めるバイト列として返す。
    ファイルへの永続的な書き出しは行わない。
    """
    global custum_vtree, name_prob_map, event_count, child_map, v_map
    event_count = 0
    custum_vtree = []
    name_prob_map = []
    child_map = {}
    v_map = {}

    queue = deque([top_gate])
    order_event = [top_gate]
    visited_event = set()
    elim_DAG = {}
    basic_sum = {}

    def Counter(event):
        if event in basic_sum:
            return basic_sum[event]
        elif event not in gate_map:
            basic_sum[event] = 1
            return basic_sum[event]
        basic_sum[event] = 0
        for child_event in gate_map[event].children:
            if child_event[0] == '~':
                child_event = child_event.removeprefix('~')
            basic_sum[event] += Counter(child_event)
        return basic_sum[event]

    Counter(top_gate)
    #print(basic_sum)

    queue = deque([top_gate])
    order_event = [top_gate]
    visited_event = set()

    def DFS(event):
        visited_event.add(event)
        if event in gate_map:
            elim_DAG[event] = []
            sorted_children = sorted(
            gate_map[event].children,
            key=lambda child: (
                basic_sum[child.removeprefix("~")],
                child.removeprefix("~")
                )
            )
            for child_event in sorted_children:
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
