import os
import shutil
import subprocess
import sys
from pathlib import Path

from .utils import Dict, dict_writer

# name of output file
KEY_OUTPUT = "output"

# file type of output: 'executable' or 'library'
KEY_TYPE = "type"

# Builder options.
KEY_DEBUG = "false"  # build as debug
KEY_DEPENDS = "depends"  # depend binaries
KEY_COMPILER = "cc"  # compiler path

# folders
KEY_FOLDERS = "folders"
KEY_FOLDERS_TOPDIR = ""
KEY_FOLDERS_BUILD = "build"
KEY_FOLDERS_INCLUDE = "include"
KEY_FOLDERS_SOURCE = "source"

# flags
KEY_FLAGS = "flags"
KEY_FLAGS_COMMON = "common"
KEY_FLAGS_DEBUG = "debug"
KEY_FLAGS_RELEASE = "release"
KEY_FLAGS_LINKER = "[linker]"

# constant values
VALUE_TYPE_EXECUTABLE = "executable"
VALUE_TYPE_LIBRARY = "library"

#
# Default contexts.
#
g_default_context = {
    "executable": {
        KEY_OUTPUT: "a.out",
        KEY_TYPE: VALUE_TYPE_EXECUTABLE,
        KEY_DEBUG: "false",
        KEY_DEPENDS: [],
        KEY_COMPILER: "g++",
        KEY_FOLDERS: {
            KEY_FOLDERS_TOPDIR: "",
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
    "library": {
        KEY_OUTPUT: "lib.a",
        KEY_TYPE: VALUE_TYPE_LIBRARY,
        KEY_DEBUG: "false",
        KEY_DEPENDS: [],
        KEY_COMPILER: "g++",
        KEY_FOLDERS: {
            KEY_FOLDERS_TOPDIR: "lib",
            KEY_FOLDERS_BUILD: "build",
            KEY_FOLDERS_INCLUDE: "include",
            KEY_FOLDERS_SOURCE: "src",
        },
        KEY_FLAGS: {
            KEY_FLAGS_COMMON: "-std=c++20",
            KEY_FLAGS_RELEASE: "-O3",
            KEY_FLAGS_DEBUG: "-O0 -g",
        },
    },
}


#
# Builder:
#   Interface of building from a context
#
class Builder:
    def __init__(self, name: str, ctx: Dict) -> None:
        self.name = name
        self.completed = False
        self.is_compiled = False

        if KEY_TYPE in ctx.keys():
            self.context = dict_writer(
                g_default_context[ctx[KEY_TYPE]],
                ctx,
                True,
                True,
            )
        else:
            self.context = dict_writer(g_default_context["executable"], ctx, True, True)

        self.sources = self.get_all_sources()
        self.output = self.get_output()

    @staticmethod
    def get_default_context() -> Dict:
        return g_default_context

    @staticmethod
    def get_dependencies(dfile: Path) -> list[str] | None:
        if not dfile.exists():
            return None

        with dfile.open(mode="r") as fs:
            tmp = fs.read().strip().replace("\\\n", "").split("\n")[0].split(": ")[1]
            tmp2 = []

            i = 0
            while " " in tmp:
                i = tmp.find(" ")
                tmp2.append(tmp[:i])
                tmp = tmp[i + 1 :].lstrip()

            return tmp2 + [tmp]

    def get_output(self) -> Path:
        output = str(self.context[KEY_OUTPUT])

        # if running on Windows, change extension
        if self.context[KEY_TYPE] == VALUE_TYPE_EXECUTABLE:
            win_ext = ".exe"

            if os.name == "nt" and not output.endswith(win_ext):
                output += win_ext
        # if library
        elif self.context[KEY_TYPE] == VALUE_TYPE_LIBRARY:
            if not output.endswith(".a"):
                output += ".a"

        return Path(output)

    def get_all_sources(self) -> list[Path]:
        path = Path(self.context[KEY_FOLDERS][KEY_FOLDERS_SOURCE])
        return list(path.glob("**/*.cpp"))

    def is_compile_needed(self, path: Path) -> bool:
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
        ctx = self.context[KEY_FLAGS]
        flag = str(ctx[KEY_FLAGS_COMMON]).split(" ")

        if self.context[KEY_DEBUG] == "true":
            flag.extend(str(ctx[KEY_FLAGS_DEBUG]).split(" "))
        else:
            flag.extend(str(ctx[KEY_FLAGS_RELEASE]).split(" "))

        flag.extend(["-I", self.context[KEY_FOLDERS][KEY_FOLDERS_INCLUDE]])

        return flag

    # compile a source file
    def compile(self, path: Path) -> None:
        build = Path(self.context[KEY_FOLDERS][KEY_FOLDERS_BUILD])
        build.mkdir(exist_ok=True)

        # create sub folders
        if len(list(self.ignore_source_dir(path).parents)) > 1:
            (build / path.parent).mkdir(parents=True, exist_ok=True)

        cc = self.context[KEY_COMPILER]
        flag = self.get_flag()

        dfile = self.as_depend_path(path)
        obj = self.as_object_path(path)

        if not self.is_compile_needed(path):
            return

        print(path)
        command = [cc, *flag, "-MP", "-MMD", "-MF", dfile, "-c", "-o", obj, path]
        res = subprocess.run(command)

        if res.returncode != 0:
            sys.exit(res.returncode)

        self.is_compiled = True

    def link(self) -> None:
        flag = self.context[KEY_FLAGS][KEY_FLAGS_LINKER]

        if self.context[KEY_DEBUG] == "true":
            flag = flag[KEY_FLAGS_DEBUG]
        else:
            flag = flag[KEY_FLAGS_RELEASE]

        if flag != "":
            flag = "-Wl," + ",".join(flag)

        print("linking...")

        command = []
        objects = [str(self.as_object_path(x)) for x in self.sources]

        if self.context[KEY_TYPE] == VALUE_TYPE_EXECUTABLE:
            command = [self.context[KEY_COMPILER], "-o", self.output, flag] + objects
        elif self.context[KEY_TYPE] == VALUE_TYPE_LIBRARY:
            command = ["ar", "rcs", self.output] + objects

        subprocess.run(command)

    #
    # Let's build !
    #
    def build(self) -> bool:
        for source in self.sources:
            self.compile(source)

        if not self.output.exists() or self.is_compiled:
            self.link()
        else:
            print("Already up to date.")

        return True

    #
    # clean
    #
    def clean(self) -> None:
        # remove output file
        self.output.unlink(missing_ok=True)

        # remove objects directory
        if os.path.isdir(x := self.context[KEY_FOLDERS][KEY_FOLDERS_BUILD]):
            shutil.rmtree(x)
