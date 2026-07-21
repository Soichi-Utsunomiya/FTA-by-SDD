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

def last_visit_BFS_vtree(top_gate, var_map, gate_map, vtree_file):
    global custum_vtree, name_prob_map, event_count, child_map
    event_count = 0
    custum_vtree.clear()
    name_prob_map.clear()
    child_map.clear()

    # --- 修正点1: まず全ノードの「参照回数（入次数）」をカウントする ---
    ref_count = {}
    temp_queue = deque([top_gate])
    visited = set([top_gate])
    
    while temp_queue:
        curr = temp_queue.popleft()
        if curr in gate_map:
            for child in gate_map[curr].children:
                child_name = child.removeprefix('~') if child.startswith('~') else child
                # 呼ばれるたびにカウントを増やす
                ref_count[child_name] = ref_count.get(child_name, 0) + 1
                if child_name not in visited:
                    visited.add(child_name)
                    temp_queue.append(child_name)

    # --- 修正点2: 参照回数を使った Last Visit BFS (トポロジカルソート) ---
    queue = deque([top_gate])
    order_event = []

    while queue:
        event = queue.popleft()
        order_event.append(event) # 全ノードが確実に1回だけ配列に入る

        if event in gate_map:
            for child in gate_map[event].children:
                child_name = child.removeprefix('~') if child.startswith('~') else child
                # 親が1つ処理されるたびにカウントを減らす
                ref_count[child_name] -= 1
                
                # カウントが0になった = 全ての親ゲートの処理が終わった (これが Last Visit!)
                if ref_count[child_name] == 0:
                    queue.append(child_name)

    # --- 修正点3: 重複のない配列を逆順に処理して vtree 構築 ---# --- 修正点: 変数が複数のゲートに重複して割り当てられるのを防ぐセット ---
    assigned_nodes = set()
    child_num = {}

    for event in reversed(order_event):
        if event in gate_map:
            valid_event = []
            for child_event in gate_map[event].children:
                child_name = child_event.removeprefix('~') if child_event.startswith('~') else child_event
                
                # 修正: まだ他の(より深い)ゲートに割り当てられていない場合のみ追加
                if child_num.get(child_name, 0) == 1 and child_name not in assigned_nodes:
                    valid_event.append(child_name)
                    assigned_nodes.add(child_name)  # 「この変数は私が引き取った」とマーキング
                    
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

    top = []
    top.append("vtree " + str(event_count))
    custum_vtree = top + custum_vtree

    with open(vtree_file, "w") as out:
        for row in custum_vtree:
            print(row, file = out)