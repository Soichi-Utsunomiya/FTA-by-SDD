from FT_to_dnf import xml_to_formula, formula_to_dnf, prob_map, gate_child_map, gate_grandchild_map
from dnf_to_sdd import run_sdd_from_pyeda_obj
from explore import explore
from BFS_vtree import BFS_vtree, child_map
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

    prob_map.clear()
    gate_child_map.clear()
    gate_grandchild_map.clear()
    
    start_time = time.perf_counter()
    """
    # 1. XML -> 論理式文字列
    formula_str = xml_to_formula(xml_file)
    print("--- Expression ---")
    print(formula_str)
    
    # 2. 文字列 -> PyEDAオブジェクト (DNF化)
    dnf_expr = formula_to_dnf(formula_str)"""
    
    print("\n--- Making vtree ---")
    BFS_vtree(xml_file, vtree_folder + file_name + ".vtree")

    # 3. PyEDAオブジェクト -> SDD
    sdd_node = run_sdd_from_pyeda_obj(xml_file, output_folder + file_name, vtree_folder + file_name + ".vtree")

    probability = explore(sdd_node)
    print(f"Probability:{probability}")

    print(f"Nodes:{sdd_node.size()}")

    end_time = time.perf_counter()
    print(f"Time:{(end_time-start_time)*1000}ms\n")

if __name__ == "__main__":
    main()