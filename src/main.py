from dnf_to_sdd import run_sdd_from_pyeda_obj
from explore import *
from BFS_vtree import BFS_vtree, child_map
from read_FT import read_FT
import os
import sys
from pathlib import Path
import time

def main():
    if len(sys.argv)>1:
        xml_file = Path(sys.argv[1])
        path = os.getcwd()
        vtree_folder = path + "/vtree"
        output_folder = path + "/output"
        file_name = xml_file.stem
    else:
        xml_file = "FTA/sample.xml"
        vtree_folder = "vtree"
        output_folder = "output"
        file_name = "sample"

    vtree_folder += '/'
    output_folder += '/'

    print(file_name)

    start_time = time.perf_counter()
    
    print("\n--- Making vtree ---")

    top_gate, var_map, gate_map, par_map = read_FT(xml_file)
    BFS_vtree(top_gate, var_map, gate_map, vtree_folder + file_name + ".vtree")

    sdd_node = run_sdd_from_pyeda_obj(top_gate, var_map, gate_map, output_folder + file_name, vtree_folder + file_name + ".vtree")

    #probability = explore(sdd_node)
    print(par_map)
    evaluator = SDDEvaluator(par_map)
    probability = evaluator.explore(sdd_node)
    print(f"Probability:{probability}")

    print(f"Nodes:{sdd_node.size()}")

    end_time = time.perf_counter()
    print(f"Time:{(end_time-start_time)}s\n")

if __name__ == "__main__":
    main()