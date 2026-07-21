from dnf_to_sdd import run_sdd_from_pyeda_obj
from explore import SDDEvaluator
from BFS_vtree import BFS_vtree
from read_FT import read_FT
import sys
import time
from pathlib import Path


def main():
    if len(sys.argv) > 1:
        xml_files = [Path(sys.argv[i]) for i in range(1, len(sys.argv))]
    else:
        xml_files = [Path("FTA/baobab3.xml")]

    start_time = time.perf_counter()

    top_gate, var_map, gate_map, par_map = read_FT(xml_files)
    if top_gate is None:
        print("This tree is not Fault Tree!")
        return

    # vtreeをバイト列として生成（ファイルI/Oなし）
    vtree_bytes = BFS_vtree(top_gate, var_map, gate_map)

    # vtree_bytesを一時ファイル経由でPySDDに渡し、直後に削除
    sdd_node, sdd_manager = run_sdd_from_pyeda_obj(
        top_gate, var_map, gate_map, vtree_bytes
    )

    evaluator = SDDEvaluator(par_map)
    probability = evaluator.explore(sdd_node)
    end_time = time.perf_counter()

    print(f"Probability:{probability}")
    print(f"Nodes:{sdd_node.size()}")
    print(f"Time:{end_time - start_time}s\n")


if __name__ == "__main__":
    main()
