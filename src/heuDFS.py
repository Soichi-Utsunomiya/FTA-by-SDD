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

def hDFS_vtree(top_gate, var_map, gate_map):
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

    basic_sum = {}
    parents = {}

    #ゲートの下に存在する基本事象をすべて数え上げる。
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
            if child_event not in parents:
                parents[child_event] = set()
            parents[child_event].add(event)
            basic_sum[event] += Counter(child_event)
        return basic_sum[event]

    Counter(top_gate)
    #print(basic_sum)
    #print(parents)
    #print(gate_levels)

    #order_event = [top_gate]
    visited_event = set()
    queue = deque([top_gate])
    B_elim_DAG = {}

    while queue:
        event = queue.popleft()
        visited_event.add(event)
        if event in gate_map:
            B_elim_DAG[event] = []
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
                    queue.append(child_event)
                    #order_event.append(child_event)
                    B_elim_DAG[event].append(child_event)
                    visited_event.add(child_event)

    #order_event = [top_gate]
    D_elim_DAG = {}
    visited_event = set()

    def DFS(event):
        visited_event.add(event)
        if event in gate_map:
            D_elim_DAG[event] = []
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
                    #order_event.append(child_event)
                    D_elim_DAG[event].append(child_event)
                    DFS(child_event)
    DFS(top_gate)

    shared_events = {}
    elim_DAG = {}
    put = set()
    for k,v in B_elim_DAG.items():
        if v != D_elim_DAG[k]:
            dif = set(v) ^ set(D_elim_DAG[k])
            elim_DAG[k] = set(v) & set(D_elim_DAG[k])
            for shared_event in dif:
                if shared_event not in shared_events:
                    shared_events[shared_event] = k
                    put.add(k)
                else:
                    if basic_sum[k] < basic_sum[shared_events[shared_event]]:
                        elim_DAG[k].add(shared_event)
                    else:
                        elim_DAG[shared_events[shared_event]].add(shared_event)
                    put.add(k)
                    print(shared_event)
                    print(shared_events[shared_event],elim_DAG[shared_events[shared_event]])
                    print(k,elim_DAG[k])

            print(k,basic_sum[k],v,D_elim_DAG[k],dif)
        else:
            elim_DAG[k] = v

    for event in put:
        elim_DAG[event] = sorted(
        elim_DAG[event],
        key=lambda child: (
            basic_sum[child.removeprefix("~")],
            child.removeprefix("~")
            )
        )

    #print(elim_DAG)
    queue = deque([top_gate])
    visited_event = set()
    order_event = [top_gate]

    while queue:
        event = queue.popleft()
        visited_event.add(event)
        if event in elim_DAG:
            for child_event in elim_DAG[event]:
                if child_event[0] == '~':
                    child_event = child_event.removeprefix('~')
                if child_event not in visited_event:
                    queue.append(child_event)
                    order_event.append(child_event)
                    visited_event.add(child_event)

    #print(order_event)
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
        else:
            child_num[event] = 1
            custum_vtree.append("L " + str(event_count) + " " + str(var_map[event]))
            v_map[event] = event_count
            #print(f"{event}:{var_map[event]}")
            event_count += 1

    lines = ["vtree " + str(event_count)] + custum_vtree
    #print(lines)
    return "\n".join(lines).encode()


def hDFS_vtree_to_tempfile(top_gate, var_map, gate_map):
    """
    vtreeのバイト列を一時ファイルに書き出し、
    そのパスを返す。呼び出し元で削除すること。
    """
    vtree_bytes = hDFS_vtree(top_gate, var_map, gate_map)
    tmp = tempfile.NamedTemporaryFile(
        mode='wb', suffix='.vtree', delete=False
    )
    tmp.write(vtree_bytes)
    tmp.close()
    return tmp.name
