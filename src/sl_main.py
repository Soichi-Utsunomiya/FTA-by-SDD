from dnf_to_sdd import run_sdd_from_pyeda_obj
from explore import SDDEvaluator
from sl_BFS_vtree import BFS_vtree
from sl_DFS_vtree import DFS_vtree
from heuDFS import hDFS_vtree
from BDD_vtree import BDD_vtree,run_dynamic_sdd_from_pyeda_obj
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
        vtree_bytes, gate_children, basic_parents, ref_count = hDFS_vtree(top_gate, var_map, gate_map)

        sdd_node, sdd_manager = run_sdd_from_pyeda_obj(
            top_gate, var_map, gate_map, vtree_bytes, gate_children, basic_parents, ref_count,
            trace_path
        )
    
    elif method == "BDD" or method == "dynamic":
        trace_path="/workspace/bdd_trace.csv"
        vtree_bytes, gate_children, basic_parents, ref_count = BDD_vtree(top_gate, var_map, gate_map)
        if method == "BDD":
            sdd_node, sdd_manager = run_sdd_from_pyeda_obj(
                top_gate, var_map, gate_map, vtree_bytes, gate_children, basic_parents, ref_count,
                trace_path
            )
        else:
            sdd_node, sdd_manager = run_dynamic_sdd_from_pyeda_obj(
                top_gate, var_map, gate_map, vtree_bytes, gate_children, basic_parents, ref_count,
                trace_path
            )
            

    end_time = time.perf_counter()
    construction_time = end_time - start_time
    
    sdd_node.ref()
    minimize_time = 0
    """if method == "dynamic":

        try:
            # vtree探索の制限
            sdd_manager.set_vtree_search_time_limit(300)
            sdd_manager.set_vtree_operation_time_limit(10)
            sdd_manager.set_vtree_operation_memory_limit(1.5)

            print("Start dynamic vtree minimization...", flush=True)

            minimize_start = time.perf_counter()
            sdd_manager.minimize_limited()
            minimize_end = time.perf_counter()
            minimize_time = minimize_end - minimize_start

            print(
                f"Minimize Time: {minimize_time}s",
                flush=True
            )
            print(f"Nodes after minimize: {sdd_node.size()}", flush=True)

        finally:
            sdd_node.deref()"""
    #else:
    sdd_node.deref()

    evaluator = SDDEvaluator(par_map)
    start_time = time.perf_counter()
    probability = evaluator.explore(sdd_node)
    end_time = time.perf_counter()
    calucuration_time = end_time - start_time

    if probability != 0:
        probability = probability.quantize(
            Decimal(1).scaleb(probability.adjusted() - 5),
            rounding=ROUND_HALF_UP
        )

    print(f"Probability:{probability}")
    print(f"Nodes:{sdd_node.size()}")
    print(f"Construction Time:{construction_time}s\n")
    #with open("output/sdd.dot", "w") as out:
    #    print(sdd_node.dot(), file = out)
    #with open("output/vtree.dot", "w") as out:
    #    print(sdd_manager.vtree().dot(), file = out)

if __name__ == "__main__":
    main()
