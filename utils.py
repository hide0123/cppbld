from typing import Any, TypeAlias

Dict: TypeAlias = dict[str, Any]

#
# dict_writer:
#   overwrite or mix a dictionaries
#
def dict_writer(
    dist: Dict, src: Dict, over_write: bool = False, mix: bool = False
) -> Dict:
    for k in src.keys():
        if not over_write and k in dist.keys():
            continue

        if (
            mix
            and k in dist.keys()
            and isinstance(dist[k], dict)
            and isinstance(src[k], dict)
        ):
            dist[k] = dict_writer(dist[k], src[k], over_write, mix)
        else:
            dist[k] = src[k]

    return dist

