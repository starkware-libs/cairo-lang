import os
import subprocess
import sys


def main():
    script_path = os.path.join(os.path.dirname(__file__), "fixed_cairo_compile.sh")
    # Second argument to the script is the path to the Python interpreter.
    args = [script_path, sys.executable] + sys.argv[1:]

    print("[INFO] Delegating to fixed_cairo_compile.sh:", " ".join(args), file=sys.stderr)
    subprocess.run(args, check=True)


if __name__ == "__main__":
    main()
