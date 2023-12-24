import json
import argparse
from builder import Builder
from driver import Driver

G_APP_VERSION = "0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(description="build C++ sources.")
    parser.add_argument("--dump-config")
    parser.add_argument("-clean", nargs="*")
    parser.add_argument("-re", nargs="*")
    parser.add_argument("-target", nargs="+")
    parser.add_argument("-j", action="store_true")

    args = parser.parse_args()

    # dump config
    if args.dump_config is not None:
        if args.dump_config not in Builder.get_default_context().keys():
            print(f"{args.dump_config} is not config type")
        else:
            print(json.dumps(
                Builder.get_default_context()[args.dump_config], indent=4))

        return

    driver = Driver("build.json")
    driver.is_thread = args.j

    # clean
    if args.clean == []:
        # 名前指定なし => 全て削除
        driver.clean_all()
        return
    elif args.clean is not None:
        # 名前指定ある => 指定されたやつだけ削除
        for name in args.clean:
            driver.get_builder(name).clean()

        return

    # re
    if args.re == []:
        driver.clean_all()
    elif args.re is not None:
        for name in args.re:
            driver.get_builder(name).clean()

    # target
    if args.target is not None:
        for name in args.target:
            driver.get_builder(name).build()
    else:
        driver.build_all()


if __name__ == "__main__":
    main()
