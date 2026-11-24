from collections import deque


def hDFS_vtree(top_gate, var_map, gate_map):

    global custum_vtree, event_count
    event_count = 0
    custum_vtree = []
    v_map = {}

    order_event = [top_gate]
    visited_event = set()
    elim_DAG = {}
    basic_parents = {}
    gate_children = {}
    ref_count = {}
    
    def Counter(event):
        if event in gate_children:
            return gate_children[event]
        gate_children[event] = 0
        for child_event in gate_map[event].children:
            if child_event[0] == '~':
                child_event = child_event.removeprefix('~')
            ref_count[child_event] = ref_count.get(child_event, 0) + 1
            if child_event not in gate_map:
                if child_event not in basic_parents:
                    basic_parents[child_event] = []
                basic_parents[child_event].append(event)
                gate_children[event] += 1
            else:  
                gate_children[event] += Counter(child_event)
        return gate_children[event]

    ref_count[top_gate] = 1
    Counter(top_gate)
    print(basic_parents)

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
                #len(gate_children[child.removeprefix("~")]),
                gate_children[child.removeprefix("~")],
                child.removeprefix("~")
            )   
        )
        sorted_children[g] = sorted_basic_events + sorted_gate_events
        #print(sorted_children[g])

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

    def build_balanced_subTree(children):
        global event_count

        if len(children) == 1:
            if children[0] in v_map:
                return v_map[children[0]]
            else:
                return children[0]

        mid = len(children) // 2
        left = build_balanced_subTree(children[:mid])
        right = build_balanced_subTree(children[mid:])

        custum_vtree.append("I " + str(event_count) + " " + str(left) + " " + str(right))
        event_count += 1
        return event_count - 1

    def build_right_subTree(children):
        global event_count

        if len(children) == 1:
            if children[0] in v_map:
                return v_map[children[0]]
            else:
                return children[0]

        mid = 1
        left = build_right_subTree(children[:mid])
        right = build_right_subTree(children[mid:])

        custum_vtree.append("I " + str(event_count) + " " + str(left) + " " + str(right))
        event_count += 1
        return event_count - 1

    def build_subTree(basics,gates):

        global event_count

        def build_basic_subTree(basics):
            groups = {}
            order = []
            for basic in basics:
                parents = tuple(sorted(basic_parents[basic]))
                groups.setdefault(parents, []).append(basic)
            for parents, basics_group in groups.items():
                #print(parents, basics_group)
                order.append(build_balanced_subTree(basics_group))
            return build_balanced_subTree(order)

        if len(basics) > 0 and len(gates) > 0:
            left = build_basic_subTree(basics)
            right = build_balanced_subTree(gates)
            custum_vtree.append("I " + str(event_count) + " " + str(left) + " " + str(right))
            event_count += 1
            return event_count - 1
        
        elif len(basics) > 0:
            return build_basic_subTree(basics)
        else:
            return build_balanced_subTree(gates)

    shape = "righ"

    for event in reversed(order_event):
        if event in elim_DAG:
            #print(event,end=":")
            valid_basics = []
            valid_gates = []
            for child_event in elim_DAG[event]:
                if child_num[child_event] == 1:
                    if child_event in basic_parents:
                        valid_basics.append(child_event)
                    else:
                        valid_gates.append(child_event)
            valid_event = valid_basics+valid_gates
            #print(gate_map[event].gate_type)

            if len(valid_event) > 0:
                if shape == "balanced":
                    v_map[event] = build_balanced_subTree(valid_event)
                elif shape == "right" or gate_map[event].gate_type == "ATLEAST":
                    v_map[event] = build_right_subTree(valid_event)
                else:
                    v_map[event] = build_subTree(valid_basics,valid_gates)
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
    return "\n".join(lines).encode(), gate_children, basic_parents, ref_count