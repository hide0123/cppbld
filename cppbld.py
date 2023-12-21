import glob
import json
import os
import sys
from pathlib import Path

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


def dict_writer(dist: dict, src: dict, overWrite=False, mix=False) -> dict:
    for k in src.keys():
        if not overWrite and k in dist.keys():
            continue

        if mix and k in dist.keys() and type(dist[k]) is type(src[k]) is dict:
            dist[k] = dict_writer(dist[k], src[k], overWrite, mix)
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

    def get_all_sources(self) -> list:
        return glob.glob(
            f"{self.context[KEY_FOLDERS][KEY_FOLDERS_SOURCE]}/**/*.cpp", recursive=True
        )

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

    def as_depend_path(self, path) -> Path:
        return Path(
            self.context[KEY_FOLDERS][KEY_FOLDERS_BUILD]
            + "/"
            + path[
                len(self.context[KEY_FOLDERS][KEY_FOLDERS_SOURCE]) + 1 : path.rfind(".")
            ]
            + ".d"
        )

    def as_object_path(self, path) -> Path:
        return Path(
            self.context[KEY_FOLDERS][KEY_FOLDERS_BUILD]
            + "/"
            + path[
                len(self.context[KEY_FOLDERS][KEY_FOLDERS_SOURCE]) + 1 : path.rfind(".")
            ]
            + ".o"
        )

    def get_flag(self):
        flag = self.context[KEY_FLAGS][KEY_FLAGS_COMMON] + " "

        if self.context[KEY_DEBUG] == "true":
            flag += self.context[KEY_FLAGS][KEY_FLAGS_DEBUG]
        else:
            flag += self.context[KEY_FLAGS][KEY_FLAGS_RELEASE]

        flag += " -I" + self.context[KEY_FOLDERS][KEY_FOLDERS_INCLUDE]

        return flag

    # compile a source file
    def compile(self, path: str):
        # create sub folder
        if "/" in path:
            dirs = path.split("/")[:-1]
            os.system(
                f'mkdir -p {self.context[KEY_FOLDERS][KEY_FOLDERS_BUILD]}/{"/".join(dirs)}'
            )

        cc = self.context[KEY_COMPILER]
        flag = self.get_flag()

        dfile = self.as_depend_path(path)
        obj = self.as_object_path(path)

        # depends = self.get_dependencies(dfile)

        if not self.is_compile_needed(path):
            return

        print(path)
        os.system(f"{cc} {flag} -MP -MMD -MF {dfile} -c -o {obj} {path}")

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
        os.system(
            f'{self.context[KEY_COMPILER]} -o {self.output} {flag} {" ".join([str(self.as_object_path(x)) for x in self.sources])}'
        )

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
        self.builders = {}

        with open(json_path, mode="r", encoding="utf-8") as fs:
            tmp = json.loads(fs.read())

            for k in tmp.keys():
                self.builders[k] = Builder(k, tmp[k])

    def build_all(self):
        for k in self.builders.keys():
            builder = self.builders[k]

            builder.build()


def main(argv):
    d = Driver("build.json")

    d.build_all()


exit(main(sys.argv))
