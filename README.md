# cppbld
C++ builder

## Installation

```bash
pip install -U git+https://github.com/hide0123/cppbld.git
```

## Usage

1. Create `build.json` in your C++ project. The following is an example.

```json
{
    "config_name": {
        "output": "project_name",
        "flags": {
            "common": "-std=c++20",
            "release": "-O3",
            "debug": "-O0 -g",
            "[linker]": {
                "release": [ "--gc-sections", "-s" ]
            }
        }
    }
}
```

2. Run the following command.

```bash
cppbld
```

## Development

If you want to develop this project, please use the pre-commit hook to check the code.<br>
Before starting development, run the following command.

```bash
pip install pre-commit
pre-commit install
```

## Developers

- super9s
- hide0123
