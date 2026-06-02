from dnf_to_sdd import run_sdd_from_pyeda_obj
from explore import *
from BFS_vtree import *
from read_FT import read_FT
import os
import sys
from pathlib import Path
import time

def main():
    if len(sys.argv)>1:
        xml_files = []
        for i in range(1,len(sys.argv)):
            xml_files.append(Path(sys.argv[i]))
        path = os.getcwd()
        vtree_folder = path + "/vtree"
        output_folder = path + "/output"
        file_name = xml_files[0].stem
    else:
        xml_files = "FTA/sample.xml"
        vtree_folder = "vtree"
        output_folder = "output"
        file_name = "sample"

    vtree_folder += '/'
    output_folder += '/'

    print(file_name)

    start_time = time.perf_counter()

    top_gate, var_map, gate_map, par_map = read_FT(xml_files)
    if top_gate is None and var_map is None and gate_map is None and par_map is None:
        print("This tree is not Fault Tree!")
        return None

    BFS_vtree(top_gate, var_map, gate_map, vtree_folder + file_name + ".vtree")

    sdd_node, sdd_manager= run_sdd_from_pyeda_obj(top_gate, var_map, gate_map, output_folder + file_name, vtree_folder + file_name + ".vtree")
    
    print(par_map)
    evaluator = SDDEvaluator(par_map)
    probability = evaluator.explore(sdd_node)
    print(f"Probability:{probability}")
    
    print(f"Nodes:{sdd_node.size()}")

    end_time = time.perf_counter()
    print(f"Time:{(end_time-start_time)}s\n")

if __name__ == "__main__":
    main()