import xml.etree.ElementTree as ET
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class GateNode:
    gate_type: str
    children: List[str] = field(default=list)
    k: Optional[int] = None

class Expression(ABC):
    @abstractmethod
    def evaluate(self, time: float) -> float:
        pass

class FixedProbability(Expression):
    def __init__(self, value: float):
        self.value = value
    
    def evaluate(self, time: float) -> float:
        return self.value

class ExponentialModel(Expression):
    def __init__(self, lambda_rate: float):
        self.lambda_rate = lambda_rate

    def evaluate(self, time: float) -> float:
        return 1.0 - math.exp(-self.lambda_rate * time)
    
def read_FT(xml_file):

    mission_time = 8760.0

    def_par = {}
    gate_map = {}
    var_map = {}
    par_map = {}
    all_gates = set()
    root = ET.parse(xml_file)
    if root.find("model-data") is not None:
        tree = root.find("model-data")
    else:  
        tree = root.find("define-fault-tree")

    if tree is None:
        return None, None, None, None

    parameters = tree.findall("define-parameter")
    for parameter in parameters:
        name = parameter.get("name")
        if parameter.find("lognormal-deviate")is not None:
            lambda_rate = float(parameter.find("lognormal-deviate").find("float").get("value"))
            def_par[name] = ExponentialModel(lambda_rate)
        elif parameter.find("parameter") is not None:
            def_par[name] = def_par[parameter.find("parameter").get("name")]

    basic_events = tree.findall("define-basic-event")
    var = 1
    for basic_event in basic_events:
        name = basic_event.get("name")
        if basic_event.find("exponential")is not None:
            value = def_par[basic_event.find("exponential").find("parameter").get("name")]
            time = 1
            if basic_event.find("exponential").find("mul") is not None:
                time = float(basic_event.find("exponential").find("mul")[0].get("value"))
            par_map[var] = value.evaluate(mission_time*time)
            var_map[name] = var
            var += 1
        else:
            par_map[var] = basic_event.find("float").get("value")
            var_map[name] = var
            var += 1

    tree = root.find("define-fault-tree")
    all_children = set()
    gate_events = tree.findall("define-gate")
    for gate_event in gate_events:
        name = gate_event.get("name")
        all_gates.add(name)
        
        elem = gate_event[0]
        gate_type = elem.tag
        children = []
        k = None
        
        # パターン1: 直下が <and> や <or> などの論理演算子の場合
        if gate_type in ["and", "or", "not", "nand", "nor", "xor"]:
            for child in elem:
                if child.tag == "not":
                    child_name = child[0].get("name")
                    not_child_name = f"~{child_name}"
                    children.append(not_child_name)
                else:
                    child_name = child.get("name")
                    children.append(child_name)
                if child_name not in var_map:
                    all_children.add(child_name)
                    
        # パターン2: 直下が直接のイベントやゲート（パススルー）の場合
        elif gate_type in ["basic-event", "gate", "event", "house-event"]:
            child_name = elem.get("name")
            children.append(child_name)
            if child_name not in var_map:
                all_children.add(child_name)
            gate_type = "pass" 
        
        elif gate_type == "atleast":
            k = int(elem.get("min"))
            for child in elem:
                child_name = child.get("name")
                children.append(child_name)
                if child_name not in var_map:
                    all_children.add(child_name)
            
        gate_map[name] = GateNode(
            gate_type=gate_type,
            children=children,
            k = k
        )

    top_gates = all_gates - all_children
    if len(top_gates) > 1:
        print(f"警告: 独立したトップゲートが複数存在します {top_gates}")
        return
    elif len(top_gates) == 0:
        print("エラー: トップゲートが見つかりません（循環参照の可能性があります）")
        return
    
    top_gate = top_gates.pop()
    print(top_gate)

    return top_gate, var_map, gate_map, par_map
