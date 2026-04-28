import os
from pathlib import Path
import subprocess
import re

def draw():
    path = os.getcwd()
    file_path = Path(path + '/output')
    for file in os.listdir(file_path):
        if file.endswith(".dot"):
            graph = re.search(r'([a-zA-Z0-9]+-?_?)+', str(file))
            print(graph.group())
            cmd = r"sed 's/:[a-z]\{1,2\}//g' " + str(file_path) + "/" + graph.group() + ".dot | dot -Tpng -Gsplines=false -o " + str(file_path) + "/" + graph.group() + ".png"
            try:
                subprocess.run(cmd, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"エラーが発生しました: {e}")