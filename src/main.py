from FT_to_dnf import xml_to_formula, formula_to_dnf, prob_map, gate_child_map, gate_grandchild_map
from dnf_to_sdd import run_sdd_from_pyeda_obj
from draw import draw
from explore import explore
#from make_vtree import make_vtree
from BFS_vtree import BFS_vtree
import os
import sys
from pathlib import Path
import time

def dir_clear(get_dir):
    target_dir = Path(get_dir)

    if not target_dir.exists() or not target_dir.is_dir():
        print(f"フォルが見つかりません")
        return
    
    for item in target_dir.glob("*"):
        if item.is_file():
            item.unlink()

def main():
    if len(sys.argv)>1:
        xml_file = Path(sys.argv[1])
        path = os.getcwd()
        vtree_folder = path + "/vtree"
        output_folder = path + "/output"
    else:
        xml_file = "FTA/sample.xml"
        vtree_folder = "vtree"
        output_folder = "output"

    dir_clear(vtree_folder)
    dir_clear(output_folder)
    vtree_folder += '/'
    output_folder += '/'

    file_name = xml_file.stem
    print(file_name)

    prob_map.clear()
    gate_child_map.clear()
    gate_grandchild_map.clear()
    
    start_time = time.perf_counter()

    # 1. XML -> 論理式文字列
    formula_str = xml_to_formula(xml_file)
    print("--- Expression ---")
    print(formula_str)
    
    # 2. 文字列 -> PyEDAオブジェクト (DNF化)
    dnf_expr = formula_to_dnf(formula_str)
    
    """print("\n--- DNF Expression (PyEDA) ---")
        print(dnf_expr) """

    """print("\n--- Probabilities ---")
    for k, v in prob_map.items():
        print(f"{k}: {v}")

    print("\n--- Child map ---")
    for k, v in gate_child_map.items():
        print(f"{k}: {v}")

    print("\n--- Grandchild map ---")
    for k, v in gate_grandchild_map.items():
        print(f"{k}: {v}")

    print("\n--- Making vtree ---")"""
    #make_vtree(xml_file, dnf_expr, vtree_folder + file_name + ".vtree")
    BFS_vtree(xml_file, dnf_expr, vtree_folder + file_name + ".vtree")

    # 3. PyEDAオブジェクト -> SDD
    sdd_node, mgr, var_map = run_sdd_from_pyeda_obj(dnf_expr, output_folder + file_name, vtree_folder + file_name + ".vtree")

    probability = explore(sdd_node)
    print(f"Probability:{probability}")

    print(f"Nodes:{sdd_node.size()}")

    end_time = time.perf_counter()
    print(f"Time:{(end_time-start_time)*1000}ms\n")
    
    mode = 1
    if mode == 1:
        print("\nUpdated below files.")
        draw()

if __name__ == "__main__":
    main()