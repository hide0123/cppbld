import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# name of output file
KEY_OUTPUT = "output"

# file type of output: 'executable' or 'library'
KEY_TYPE = "type"

KEY_DEBUG = "false"
KEY_DEPENDS = "depends"
KEY_COMPILER = "cc"

KEY_FOLDERS = "folders"
KEY_FOLDERS_BUILD = "build"
KEY_FOLDERS_INCLUDE = "include"
KEY_FOLDERS_SOURCE = "source"

KEY_FLAGS = "flags"
KEY_FLAGS_COMMON = "common"
KEY_FLAGS_DEBUG = "debug"
KEY_FLAGS_RELEASE = "release"
KEY_FLAGS_LINKER = "[linker]"

g_default_context = {
    "executable": {
        KEY_OUTPUT: "",
        KEY_TYPE: "executable",
        KEY_DEBUG: "false",
        KEY_DEPENDS: [],
        KEY_COMPILER: "g++",
        KEY_FOLDERS: {
            KEY_FOLDERS_BUILD: "build",
            KEY_FOLDERS_INCLUDE: "include",
            KEY_FOLDERS_SOURCE: "src",
        },
        KEY_FLAGS: {
            KEY_FLAGS_COMMON: "-std=c++20",
            KEY_FLAGS_RELEASE: "-O3",
            KEY_FLAGS_DEBUG: "-O0 -g",
            KEY_FLAGS_LINKER: {
                KEY_FLAGS_RELEASE: ["--gc-sections", "-s"],
                KEY_FLAGS_DEBUG: [],
            },
        },
    },
    """  """ "library": {},
}


def dict_writer(
    dist: dict, src: dict, over_write: bool = False, mix: bool = False
) -> dict:
    for k in src.keys():
        if not over_write and k in dist.keys():
            continue

        if mix and k in dist.keys() and type(dist[k]) is type(src[k]) is dict:
            dist[k] = dict_writer(dist[k], src[k], over_write, mix)
        else:
            dist[k] = src[k]

    return dist


class Builder:
    def __init__(self, name: str, ctx: dict):
        self.name = name
        self.completed = False
        self.is_compiled = False

        if KEY_TYPE in ctx.keys():
            self.context = dict_writer(
                g_default_context[ctx[KEY_TYPE]], ctx, True, True  # type: ignore
            )
        else:
            self.context = dict_writer(g_default_context["executable"], ctx, True, True)  # type: ignore

        self.sources = self.get_all_sources()
        self.output = Path(self.context[KEY_OUTPUT])

    @staticmethod
    def get_dependencies(dfile: Path) -> list[str] | None:
        if not dfile.exists():
            return None

        with dfile.open(mode="r") as fs:
            tmp = fs.read()

            if "\\" not in tmp:
                tmp = tmp[: tmp.find("\n")]
                return tmp[tmp.find(":") + 1 :].strip().split(" ")

            tmp = tmp.replace(" \\\n  ", " ")
            return tmp[tmp.find(":") + 2 : tmp.find("\n\n")].strip().split(" ")

    def get_all_sources(self) -> list[Path]:
        path = Path(self.context[KEY_FOLDERS][KEY_FOLDERS_SOURCE])
        return list(path.glob("**/*.cpp"))

    def is_compile_needed(self, path) -> bool:
        if not self.as_object_path(path).exists():
            return True

        depends = Builder.get_dependencies(self.as_depend_path(path))
        time = self.as_object_path(path).stat().st_mtime

        if depends is None:
            return True

        for d in depends:
            if time < Path(d).stat().st_mtime:
                return True

        return False

    def ignore_source_dir(self, path: Path) -> Path:
        source = self.context[KEY_FOLDERS][KEY_FOLDERS_SOURCE]
        return Path(str(path)[len(source) + 1 :])

    def get_path(self, path: Path, suffix: str) -> Path:
        build = self.context[KEY_FOLDERS][KEY_FOLDERS_BUILD]
        return Path(build) / self.ignore_source_dir(path).with_suffix(suffix)

    def as_depend_path(self, path: Path) -> Path:
        return self.get_path(path, ".d")

    def as_object_path(self, path: Path) -> Path:
        return self.get_path(path, ".o")

    def get_flag(self) -> list[str]:
        flag = str(self.context[KEY_FLAGS][KEY_FLAGS_COMMON]).split(" ")

        if self.context[KEY_DEBUG] == "true":
            flag.extend(str(self.context[KEY_FLAGS][KEY_FLAGS_DEBUG]).split(" "))
        else:
            flag.extend(str(self.context[KEY_FLAGS][KEY_FLAGS_RELEASE]).split(" "))

        flag.extend(["-I", self.context[KEY_FOLDERS][KEY_FOLDERS_INCLUDE]])

        return flag

    # compile a source file
    def compile(self, path: Path):
        build = Path(self.context[KEY_FOLDERS][KEY_FOLDERS_BUILD])
        build.mkdir(exist_ok=True)

        # create sub folders
        if len(list(self.ignore_source_dir(path).parents)) > 1:
            (build / path.parent).mkdir(parents=True, exist_ok=True)

        cc = self.context[KEY_COMPILER]
        flag = self.get_flag()

        dfile = self.as_depend_path(path)
        obj = self.as_object_path(path)

        # depends = self.get_dependencies(dfile)

        if not self.is_compile_needed(path):
            return

        print(path)
        command = [cc, *flag, "-MP", "-MMD", "-MF", dfile, "-c", "-o", obj, path]
        res = subprocess.run(command)

        if res.returncode != 0:
            sys.exit(res.returncode)

        self.is_compiled = True

    def link(self):
        flag = self.context[KEY_FLAGS][KEY_FLAGS_LINKER]

        if self.context[KEY_DEBUG] == "true":
            flag = flag[KEY_FLAGS_DEBUG]
        else:
            flag = flag[KEY_FLAGS_RELEASE]

        if flag != "":
            flag = "-Wl," + ",".join(flag)

        print("linking...")
        command = [self.context[KEY_COMPILER], "-o", self.output, flag] + [
            str(self.as_object_path(x)) for x in self.sources
        ]
        subprocess.run(command)

    def build(self) -> bool:
        for source in self.sources:
            self.compile(source)

        if not self.output.exists() or self.is_compiled:
            self.link()
        else:
            print("Already up to date.")

        return True


class Driver:
    def __init__(self, json_path: str):
        self.builders: dict[str, Builder] = {}

        with Path(json_path).open(mode="r", encoding="utf-8") as fs:
            tmp: dict[str, Any] = json.loads(fs.read())

            for k in tmp.keys():
                self.builders[k] = Builder(k, tmp[k])

    def build_all(self):
        for k in self.builders.keys():
            builder = self.builders[k]

            builder.build()


def main():
    d = Driver("build.json")
    d.build_all()


if __name__ == "__main__":
    main()
