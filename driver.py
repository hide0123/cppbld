import json
import concurrent.futures
from pathlib import Path
from builder import Builder
from utils import Dict


#
# Driver
#
class Driver:
    def __init__(self, json_path: str) -> None:
        self.builders: dict[str, Builder] = {}
        self.is_thread = False

        try:
            with Path(json_path).open(mode="r", encoding="utf-8") as fs:
                tmp: Dict = json.loads(fs.read())

                for k in tmp.keys():
                    self.builders[k] = Builder(k, tmp[k])
        except FileNotFoundError:
            print("'build.json' is not found in current directory.")
            exit(1)

    def get_builder(self, name) -> Builder:
        if name not in self.builders.keys():
            print(f"doensn't exists the context of '{name}' in build.json")
            exit()

        return self.builders[name]

    def build_all(self) -> None:
        if self.is_thread:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(Builder.build, [self.builders[k] for k in self.builders.keys()])
        else:
            for k in self.builders.keys():
                self.builders[k].build()

    def clean_all(self) -> None:
        if self.is_thread:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(Builder.clean, [self.builders[k] for k in self.builders.keys()])
        else:
            for k in self.builders.keys():
                self.builders[k].clean()
