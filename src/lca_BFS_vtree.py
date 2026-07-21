from collections import deque, defaultdict

v_map = {}
child_map = {}
name_prob_map = []
custum_vtree = []
event_count = 0

def build_balanced_subTree(children):
    global event_count, v_map, child_map

    if len(children) == 1:
        child = children[0]
        if isinstance(child, int):
            return child
        else:
            return v_map[child]

    mid = len(children) // 2
    left = build_balanced_subTree(children[:mid])
    right = build_balanced_subTree(children[mid:])

    custum_vtree.append("I " + str(event_count) + " " +  str(left) + " " + str(right))
    event_count += 1
    return event_count-1

def build_right_subTree(children):
    global event_count, v_map, child_map

    if len(children) == 1:
        child = children[0]
        if isinstance(child, int):
            return child
        else:
            return v_map[child]

    left_child = children[0]
    if isinstance(left_child, int):
        left = left_child
    else:
        left = v_map[left_child]
    right = build_right_subTree(children[1:])

    custum_vtree.append("I " + str(event_count) + " " +  str(left) + " " + str(right))
    event_count += 1
    return event_count-1

# paths は [(事象名, [LCAからの経路]), ...] のリスト
def build_topological_subTree(paths):
    # 1. 経路が空（末端の基本事象に到達）なら、その事象を返す
    if len(paths) == 1 and len(paths[0][1]) == 0:
        return paths[0][0] # 基本事象の名前 (例: 'e1')

    # 2. 次のゲート（経路の先頭）でグループ化する
    groups = defaultdict(list)
    for event_name, path in paths:
        if len(path) == 0:
            # 経路がない場合はそのままグループ化（通常は発生しないよう調整）
            groups[event_name].append((event_name, path))
        else:
            next_gate = path[0]
            # 経路の先頭を取り除いてグループに追加
            groups[next_gate].append((event_name, path[1:]))

    # 3. 各グループ（子ゲートのまとまり）に対して再帰的にvtreeを構築
    subtrees = []
    for group_key, group_paths in groups.items():
        # 再帰呼び出しで、下層のFT構造を反映したvtreeの根のIDを取得
        subtree_root = build_topological_subTree(group_paths)
        subtrees.append(subtree_root)

    # 4. 現在の階層で、完成した部分木同士を結合する
    # ※ここは依存関係の強い「塊（モジュール）」同士の結合なので、
    # バランス木（build_balanced_subTree）で結合してOKです。
    return build_balanced_subTree(subtrees)

def extract_fast_path(lca_gate, target_event, first_parent):
    path = []
    curr = target_event
    # ターゲットから親を辿り、LCAまで遡る
    while curr != lca_gate:
        path.append(curr)
        curr = first_parent[curr]
    path.append(lca_gate)
    
    path.reverse() # 上からの順序に反転
    return path

def lca_BFS_vtree(top_gate, var_map, gate_map, vtree_file):
    global custum_vtree, name_prob_map, event_count, child_map
    event_count = 0
    custum_vtree.clear()
    name_prob_map.clear()
    child_map.clear()

    queue = deque([top_gate])
    order_event = [top_gate]
    visited_event = set()
    elim_DAG = {}
    shared_basic_events = set()
    first_parent = {}

    while queue:
        event = queue.popleft()
        visited_event.add(event)
        if event in gate_map:
            elim_DAG[event] = []
            for child_event in gate_map[event].children:
                if child_event[0] == '~':
                    child_event = child_event.removeprefix('~')
                if child_event not in visited_event:
                    first_parent[child_event] = event
                    queue.append(child_event)
                    order_event.append(child_event)
                    elim_DAG[event].append(child_event)
                    visited_event.add(child_event)
                elif child_event not in gate_map:
                    shared_basic_events.add(child_event)

    # 事象名からビット整数に変換するための辞書
    bit_map = {}
    # ビット整数から事象名に逆引きするための辞書（LCA特定時に使います）
    rev_bit_map = {}

    # enumerateを使って、0番目、1番目、2番目...とインデックスを振る
    for i, event in enumerate(sorted(shared_basic_events)):
        bit_val = 1 << i  
        bit_map[event] = bit_val
        rev_bit_map[bit_val] = event

    dp_bit = {}
    lca_map = {}
    parents = {}
    for event in order_event:
        if event in gate_map:
            bit = 0
            for child_event in gate_map[event].children:
                if child_event[0] == '~':
                    child_event = child_event.removeprefix('~')
                if child_event in bit_map:
                    bit |= bit_map[child_event]
            dp_bit[event] = bit

    for event in reversed(order_event):
        if event in gate_map:
            lca_bit = 0
            for child_event in gate_map[event].children:
                if child_event[0] == '~':
                    child_event = child_event.removeprefix('~')
                if child_event in gate_map:
                    intersection = dp_bit[event] & dp_bit[child_event]
                    lca_bit |= intersection
                    dp_bit[event] |= dp_bit[child_event]
            if lca_bit > 0:
                for bit_val, shared_evt in rev_bit_map.items():
                    if (lca_bit & bit_val) > 0:
                        lca_map[shared_evt] = event
                        if shared_evt not in parents:
                            parents[shared_evt] = []
                        parents[shared_evt].append(event)
    rev_lca_map = {}
    for basic, gate in lca_map.items():
        if gate not in rev_lca_map:
            rev_lca_map[gate] = []
        rev_lca_map[gate].append(basic)
        parents[basic].reverse()

    print(rev_lca_map)
    child_num = {}
    for event in reversed(order_event):
        if event in elim_DAG:
            valid_event = []
            for child_event in elim_DAG[event]:
                if child_num[child_event] == 1 and child_event not in shared_basic_events:
                    valid_event.append(child_event)

            if event in rev_lca_map:
                rev_lca_map[event].reverse()
                """print(f"{event}:{rev_lca_map[event]}")
                paths = []
                for shared_evt in rev_lca_map[event]:
                    path = extract_fast_path(event, shared_evt, first_parent)
                    paths.append((shared_evt, path))
                left = build_topological_subTree(paths)"""
                left = build_balanced_subTree(rev_lca_map[event])
                if len(valid_event) > 0:
                    if gate_map[event].gate_type == "aleast":
                        right = build_balanced_subTree(valid_event)
                    else:
                        right = build_right_subTree(valid_event)
                    custum_vtree.append("I " + str(event_count) + " " +  str(left) + " " + str(right))
                    v_map[event] = event_count
                    event_count += 1
                else:
                    v_map[event] = left
                
                child_num[event] = 1
                
            elif len(valid_event) > 0:
                if gate_map[event].gate_type == "aleast":
                    v_map[event] = build_balanced_subTree(valid_event)
                else:
                    v_map[event] = build_right_subTree(valid_event)
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