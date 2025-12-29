import argparse
import os

from files.nu import NuPlatform
from files.nup import Nup


def main():
    parser = argparse.ArgumentParser(prog="nu-analyze")
    parser.add_argument("data_path")

    args = parser.parse_args()

    nups = scan_dir(args.data_path)

    alpha_modes = {}
    alpha_tests = {}
    colours = {}
    effect_ids = {}
    lightings = {}
    for nup in nups:
        with open(nup, "rb") as file:
            data = file.read()
            nup = Nup(data, NuPlatform.PC)

            for material in nup.materials:
                alpha_mode = material.alpha_mode()
                alpha_modes.setdefault(alpha_mode, 0)
                alpha_modes[alpha_mode] += 1

                alpha_test = material.alpha_test()
                alpha_tests.setdefault(alpha_test, 0)
                alpha_tests[alpha_test] += 1

                colour = material.colour()
                colours.setdefault(colour, 0)
                colours[colour] += 1

                effect_ids.setdefault(material.effect_id, 0)
                effect_ids[material.effect_id] += 1

                lighting = material.lighting()
                lightings.setdefault(lighting, 0)
                lightings[lighting] += 1

    print("attrib.alpha: {}".format(alpha_modes))
    print("attrib.colour: {}".format(colours))
    print("attrib.lighting: {}".format(lightings))
    print("attrib.atst: {}".format(alpha_tests))
    print("fxid: {}".format(effect_ids))


def scan_dir(path):
    nups = []
    for entry in os.scandir(path):
        if entry.is_dir():
            nups += scan_dir(entry.path)
        elif entry.is_file():
            _, ext = os.path.splitext(entry.path)
            if ext == ".nup":
                nups.append(entry.path)

    return nups


if __name__ == "__main__":
    main()
