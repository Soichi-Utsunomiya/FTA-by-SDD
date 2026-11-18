from dnf_to_sdd import run_sdd_from_pyeda_obj
from explore import SDDEvaluator
from sl_BFS_vtree import BFS_vtree
from sl_DFS_vtree import DFS_vtree
from heuDFS import hDFS_vtree
from BDD_vtree import BDD_vtree
from read_FT import read_FT
import sys
import time
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP


def main():
    if len(sys.argv) > 1:
        method = sys.argv[1]
        xml_files = [Path(sys.argv[i]) for i in range(2, len(sys.argv))]
    else:
        xml_files = [Path("FTA/das9701.xml")]

    start_time = time.perf_counter()

    top_gate, var_map, gate_map, par_map = read_FT(xml_files)
    if top_gate is None:
        print("This tree is not Fault Tree!")
        return

    trace_path = None

    if method == "SDD":
        #vtree_bytes = BFS_vtree(top_gate, var_map, gate_map)
        #vtree_bytes = DFS_vtree(top_gate, var_map, gate_map)
        trace_path="/workspace/sdd_trace.csv"
        vtree_bytes, gate_children, basic_parents = hDFS_vtree(top_gate, var_map, gate_map)
    
    elif method == "BDD":
        trace_path="/workspace/bdd_trace.csv"
        vtree_bytes, gate_children, basic_parents = BDD_vtree(top_gate, var_map, gate_map)

    # vtree_bytesを一時ファイル経由でPySDDに渡し、直後に削除
    sdd_node, sdd_manager = run_sdd_from_pyeda_obj(
        top_gate, var_map, gate_map, vtree_bytes, gate_children, basic_parents, 
        trace_path
    )

    evaluator = SDDEvaluator(par_map)
    probability = evaluator.explore(sdd_node)
    end_time = time.perf_counter()

    if probability != 0:
        probability = probability.quantize(
            Decimal(1).scaleb(probability.adjusted() - 5),
            rounding=ROUND_HALF_UP
        )

    sdd_node.ref()
    print(sdd_manager)

    print(f"Probability:{probability}")
    print(f"Nodes:{sdd_node.size()}")
    print(f"Time:{end_time - start_time}s\n")

    sdd_node.deref()
    #sdd_manager.garbage_collect()
    print(sdd_manager)
    #with open("output/sdd.dot", "w") as out:
    #    print(sdd_node.dot(), file = out)
    #with open("output/vtree.dot", "w") as out:
    #    print(sdd_manager.vtree().dot(), file = out)

if __name__ == "__main__":
    main()
