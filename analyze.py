import argparse
import os

from files.nu import NuPlatform
from files.nup import Nup


class PlatformInfo:
    PLATFORM_INFO = {
        "pc": {
            "ext": ".nup",
            "platform": NuPlatform.PC,
        },
        "xbox": {
            "ext": ".nux",
            "platform": NuPlatform.XBOX,
        },
    }

    def __init__(self, platform: str):
        platform_info = PlatformInfo.PLATFORM_INFO[platform]
        self.ext = platform_info["ext"]
        self.platform = platform_info["platform"]


def main():
    parser = argparse.ArgumentParser(prog="nu-analyze")
    parser.add_argument("data_path")
    parser.add_argument("--platform", choices=["xbox", "pc"], required=True)

    args = parser.parse_args()

    platform_info = PlatformInfo(args.platform)
    nup_paths = scan_dir(args.data_path, platform_info.ext)

    alpha_modes = {}
    alpha_tests = {}
    colours = {}
    effect_ids = {}
    lightings = {}
    for nup_path in nup_paths:
        nup_name = os.path.basename(nup_path)
        with open(nup_path, "rb") as file:
            data = file.read()
            try:
                nup = Nup(data, platform_info.platform)
            except:
                print("Failed to parse: {}".format(nup_name))
                continue

            for i, material in enumerate(nup.materials):
                try:
                    alpha_mode = material.alpha_mode()
                    alpha_test = material.alpha_test()
                    colour = material.colour()
                    effect_id = material.effect_id
                    lighting = material.lighting()
                except:
                    print("Failed to analyze material #{} in: {}".format(i, nup_name))
                    continue

                alpha_modes.setdefault(alpha_mode, 0)
                alpha_modes[alpha_mode] += 1

                alpha_tests.setdefault(alpha_test, 0)
                alpha_tests[alpha_test] += 1

                colours.setdefault(colour, 0)
                colours[colour] += 1

                effect_ids.setdefault(effect_id, 0)
                effect_ids[effect_id] += 1

                lightings.setdefault(lighting, 0)
                lightings[lighting] += 1

    print("attrib.alpha: {}".format(alpha_modes))
    print("attrib.colour: {}".format(colours))
    print("attrib.lighting: {}".format(lightings))
    print("attrib.atst: {}".format(alpha_tests))
    print("fxid: {}".format(effect_ids))


def scan_dir(path: str, match_ext: str):
    nups = []
    for entry in os.scandir(path):
        if entry.is_dir():
            nups += scan_dir(entry.path, match_ext)
        elif entry.is_file():
            _, ext = os.path.splitext(entry.path)
            if ext.lower() == match_ext.lower():
                nups.append(entry.path)

    return nups


if __name__ == "__main__":
    main()
