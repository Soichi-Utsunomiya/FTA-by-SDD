from FT_to_dnf import xml_to_formula, formula_to_dnf, prob_map, gate_child_map, gate_grandchild_map
from dnf_to_sdd import run_sdd_from_pyeda_obj
from draw import draw
from explore import explore
from make_vtree import make_vtree
from BFS_vtree import BFS_vtree

def main():
    xml_file = "./FTA/sddEx.xml"
    
    # 1. XML -> 論理式文字列
    formula_str = xml_to_formula(xml_file)
    print("--- Expression ---")
    print(formula_str)
    
    # 2. 文字列 -> PyEDAオブジェクト (DNF化)
    dnf_expr = formula_to_dnf(formula_str)
    
    print("\n--- DNF Expression (PyEDA) ---")
    print(dnf_expr) 

    print("\n--- Probabilities ---")
    for k, v in prob_map.items():
        print(f"{k}: {v}")

    print("\n--- Child map ---")
    for k, v in gate_child_map.items():
        print(f"{k}: {v}")

    print("\n--- Grandchild map ---")
    for k, v in gate_grandchild_map.items():
        print(f"{k}: {v}")

    #make_vtree(xml_file, dnf_expr)
    BFS_vtree(xml_file, dnf_expr)

    # 3. PyEDAオブジェクト -> SDD
    sdd_node, mgr, var_map = run_sdd_from_pyeda_obj(dnf_expr)

    #explore(sdd_node)
    
    mode = 1
    if mode == 1:
        print("\nUpdated below files.")
        draw()

if __name__ == "__main__":
    main()