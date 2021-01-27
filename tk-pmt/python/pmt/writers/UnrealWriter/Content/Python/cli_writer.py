# UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import argparse
import os
import sys

# Our directory must be in sys.path in order to import client_config
this_dir = os.path.split(__file__)[0]
if this_dir not in sys.path:
    sys.path.append(this_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pmt_mod", help="Path to pmt-core module")
    parser.add_argument("screenplay")
    args = parser.parse_args()

    sys.path.append(args.pmt_mod)
    from pmt import pmt

    pmt.translate(
        reader="screenplay",
        reader_args={"input": args.screenplay},
        writer="unreal",
        writer_args={},
    )
