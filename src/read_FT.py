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

def read_FT(xml_files):

    def record_house_events(data, prefix):
        house_events = data.findall("define-house-event")
        for house_event in house_events:
            name = house_event.get("name")
            if prefix != "":
                name = f"{prefix}.{name}"
            if house_event.find("constant").get("value") == "true":
                par_map[name] = 1
                all_basic_events.add(name)

    def record_parameters(data, prefix):
        parameters = data.findall("define-parameter")
        for parameter in parameters:
            name = parameter.get("name")
            if prefix != "":
                name = f"{prefix}.{name}"
            if parameter.find("lognormal-deviate")is not None:
                lambda_rate = float(parameter.find("lognormal-deviate").find("float").get("value"))
                def_par[name] = ExponentialModel(lambda_rate)
            elif parameter.find("parameter") is not None:
                def_par[name] = def_par[parameter.find("parameter").get("name")]

    def record_basic_events(data, prefix):
        basic_events = data.findall("define-basic-event")
        for basic_event in basic_events:
            name = basic_event.get("name")
            if prefix != "":
                name = f"{prefix}.{name}"
            if basic_event.find("exponential")is not None:
                value = def_par[basic_event.find("exponential").find("parameter").get("name")]
                time = 1
                if basic_event.find("exponential").find("mul") is not None:
                    time = float(basic_event.find("exponential").find("mul")[0].get("value"))
                par_map[name] = value.evaluate(mission_time*time)
            else:
                par_map[name] = basic_event.find("float").get("value")
            all_basic_events.add(name)

    def record_gate_events(tree, prefix):
        gate_events = tree.findall("define-gate")
        for gate_event in gate_events:
            name = gate_event.get("name")
            if prefix != "":
                name = f"{prefix}.{name}"
            all_gates.add(name)
            print(name)
            
            elem = gate_event[0]
            if elem.tag == "label":
                elem = gate_event[1]
            gate_type = elem.tag
            children = []
            k = None
            
            # パターン1: 直下が <and> や <or> などの論理演算子の場合
            if gate_type in ["and", "or", "not", "nand", "nor", "xor"]:
                for child in elem:
                    if child.tag == "not":
                        child_name = child[0].get("name")
                        if child[0].tag == "gate":
                            if prefix != "":
                                child_name = f"{prefix}.{child_name}"
                        else:
                            if prefix != "":
                                if f"{prefix}.{child_name}" in par_map:
                                    child_name = f"{prefix}.{child_name}"
                        not_child_name = f"~{child_name}"
                        children.append(not_child_name)
                    else:
                        child_name = child.get("name")
                        if child.tag == "gate":
                            if  prefix != "":
                                child_name = f"{prefix}.{child_name}"
                        else:
                            if prefix != "":
                                if f"{prefix}.{child_name}" in par_map:
                                    child_name = f"{prefix}.{child_name}"
                        children.append(child_name)
                    if child_name not in all_basic_events:
                        all_children.add(child_name)
                    else:
                        exist_basic_events.add(child_name)
                        
            # パターン2: 直下が直接のイベントやゲート（パススルー）の場合
            elif gate_type in ["basic-event", "gate", "event", "house-event"]:
                child_name = elem.get("name")
                if elem.tag == "gate":
                    if  prefix != "":
                        child_name = f"{prefix}.{child_name}"
                else:
                    if prefix != "":
                        if f"{prefix}.{child_name}" in par_map:
                            child_name = f"{prefix}.{child_name}"
                children.append(child_name)
                if child_name not in all_basic_events:
                    all_children.add(child_name)
                else:
                    exist_basic_events.add(child_name)
                gate_type = "pass" 
            
            elif gate_type == "atleast":
                k = int(elem.get("min"))
                for child in elem:
                    child_name = child.get("name")
                    if child.tag == "gate":
                        if  prefix != "":
                            child_name = f"{prefix}.{child_name}"
                    else:
                        if prefix != "":
                            if f"{prefix}.{child_name}" in par_map:
                                child_name = f"{prefix}.{child_name}"
                    children.append(child_name)
                    if child_name not in all_basic_events:
                        all_children.add(child_name)
                    else:
                        exist_basic_events.add(child_name)
                
            gate_map[name] = GateNode(
                gate_type=gate_type,
                children=children,
                k = k
            )
    
    def process_component(component, prefix):
        name = component.get("name")
        if prefix == "":
            next_prefix = name
        else:
            next_prefix = f"{prefix}.{name}"
        
        records(component, next_prefix)
        record_gate_events(component, next_prefix)
        for child_component in component.findall("define-component"):
            process_component(child_component, next_prefix)

    def records(r, prefix):  
        record_house_events(r, prefix)
        record_parameters(r, prefix)
        record_basic_events(r, prefix)

    def synthesis(root1, root2):
        records(root1.find("model-data"), "")

        records(root2.find("define-fault-tree"), "")
        
        components = root2.find("define-fault-tree").findall("define-component")
        for component in components:
            process_component(component, "")
        
        record_gate_events(root2.find("define-fault-tree"), "")


    mission_time = 8760.0

    def_par = {}
    gate_map = {}
    all_basic_events = set()
    par_map = {}
    all_gates = set()
    all_children = set()
    exist_basic_events = set()
    if len(xml_files) == 1:
        root = ET.parse(xml_files[0])
        if root.find("model-data") is not None:
            records(root.find("model-data"), "")

        records(root.find("define-fault-tree"), "")

        components = root.find("define-fault-tree").findall("define-component")
        for component in components:
            process_component(component, "")
        
        record_gate_events(root.find("define-fault-tree"), "")
    else:
        root1 = ET.parse(xml_files[0])
        root2 = ET.parse(xml_files[1])
        if root1.find("model-data") is not None:
            synthesis(root1, root2)
        else:
            synthesis(root2, root1)

    var_map = {}
    exist_par_map = {}
    count = 1
    for var in all_basic_events and exist_basic_events:
        var_map[var] = count
        exist_par_map[count] = par_map[var]
        count += 1

    print(gate_map)
    top_gates = all_gates - all_children
    if len(top_gates) > 1:
        print(f"警告: 独立したトップゲートが複数存在します {top_gates}")
        return
    elif len(top_gates) == 0:
        print("エラー: トップゲートが見つかりません（循環参照の可能性があります）")
        return
    
    top_gate = top_gates.pop()
    print(top_gate)

    return top_gate, var_map, gate_map, exist_par_map
