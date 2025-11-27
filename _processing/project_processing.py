# TODO
# Store original code
# Clean up YAML:
#   Fix incorrect / missing dates (including 'today's)
#   Add categories (lang, intensive, dataset)
#   Check thumbnail
#   Check eval status
# Check code (assuming eval: true)
#   Check and fix all data paths
#   Check all dependencies
#   Try running code (extract code cells?)
#   Remove broken files from render list
#   Log findings

from datetime import datetime
import importlib.util
import json
import os
import re
import shutil
from subprocess import run
import sys
import warnings

import matplotlib as mpl

MONTHS = {
    "Python": {"25Summer": "Jan", "25Winter": "Jul", "26Summer": "Feb"},
    "R": {"25Summer": "Jan", "25Winter": "Jul", "26Summer": "Jan"},
    "QGIS": {"25Summer": "Jan", "25Winter": "Jul", "26Summer": "Feb"},
}
O = "\033[0m"
R = "\033[31m"
G = "\033[32m"
Y = "\033[33m"


# Source - https://stackoverflow.com/a
# Posted by Alexander C, modified by community. See post 'Timeline' for change history
# Retrieved 2025-11-24, License - CC BY-SA 4.0
class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, "w")

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout


def run_py(source):
    with HiddenPrints():
        try:
            exec(source)
        except Exception as e:
            return e
        else:
            return None


if not os.path.exists("_quarto.yml"):
    raise EnvironmentError("Not in quarto project dir.")

if sys.prefix == sys.base_prefix:
    raise EnvironmentError(
        "Not in a virtual environment, required for testing Python imports.\n\nHave you activated? Run source .venv/bin/activate"
    )

d = os.path.dirname
b = os.path.basename
j = os.path.join

if not os.path.exists(j(d(sys.prefix), "_quarto.yml")):
    raise EnvironmentError("Not in the correct virtual environment.")

warnings.filterwarnings("ignore")
mpl.use("Agg")

old_state_files = {j(path, f) for path, _, fs in os.walk("./") for f in fs}

render_list = os.getenv("QUARTO_PROJECT_INPUT_FILES")

with open("_processing/project_ok.log") as f:
    ok_projects = [ln.strip().split(",") for ln in f.readlines()]


qmds = [
    j(path, file)
    for path, _, files in os.walk("gallery")
    for file in files
    if file.endswith(".qmd") and b(d(d(d(path)))) == "gallery"
]

e_log = []

with open("renv.lock") as f:
    R_packages = json.load(f)["Packages"].keys()

with open("requirements.txt") as f:
    py_packages = [line[: line.find("==")] for line in f.readlines()]

print("Checking all projects in gallery/ for errors.")
for qmd in qmds:
    last_checks = [
        datetime.strptime(f[1], "%Y-%m-%d %H:%M:%S") for f in ok_projects if f[0] == qmd
    ]

    if last_checks != [] and datetime.fromtimestamp(os.stat(qmd).st_mtime) < max(
        last_checks
    ):
        continue

    backup_dir = j(d(qmd), "original_source")
    if not os.path.isdir(backup_dir):
        os.mkdir(backup_dir)
        shutil.copy2(qmd, j(backup_dir, ""))
    elif not os.path.exists(j(backup_dir, b(qmd))):
        shutil.copy2(qmd, j(backup_dir, ""))

    print(f"{Y}TESTING:{O}", qmd)

    # I/O
    with open(qmd) as f:
        content = f.read()

    lang = b(d(d(d(qmd))))
    iteration = b(d(d(qmd)))

    #### YAML ####
    try:
        yaml_start = content.index("---")
        yaml_end = content.index("---", yaml_start + 1)
    except ValueError:
        message = "No YAML"
        e_log.append((qmd, message))
        print(R, "\tFAILED:", O, message)
        continue

    yaml = content[:yaml_end]
    body = content[yaml_end:]

    # Spaces in YAML
    first_yaml_ln_i = content.index("\n", yaml_start) + 1
    first_yaml_arg_i = content.index(
        content[first_yaml_ln_i:].lstrip()[0], first_yaml_ln_i
    )
    spaces = content[first_yaml_ln_i:first_yaml_arg_i]

    if spaces.count(" ") != len(spaces):
        raise ValueError(f"Cannot determine spaces in {qmd}.")

    # Fix dates
    date = MONTHS[lang][iteration] + "-" + iteration[:2]

    if "Date: " in content[:yaml_end]:
        yaml = yaml.replace("Date: ", "date: ")

    if "date: " not in content[:yaml_end]:
        yaml += f"{spaces}date: {date}\n"
    elif "today" in content[:yaml_end]:
        yaml = yaml.replace("today", date)

    # Find all data paths
    data_paths = set()

    for quote in ('"', "'"):
        i = body.find(f".csv{quote}")

        while i != -1:
            data_path_start = body.rfind(quote, 0, i) + 1
            data_path_end = body.find(quote, i)

            data_paths.add(body[data_path_start:data_path_end])

            i = body.find(f".csv{quote}", data_path_end)

    # Add categories
    data_files = '", "data: '.join(
        [
            os.path.basename(data)
            for data in data_paths
            if os.path.basename(data) in os.listdir("data")
        ]
    )

    if data_files != "":
        data_files = ', "data: ' + data_files + '"'

    categories = f"{spaces}categories: [{lang}, {iteration}{data_files}]\n"

    if categories in yaml:
        pass
    elif "categories: " in yaml:
        i_cat = yaml.index("categories: ")
        cat_ln_start = yaml.rindex("\n", 0, i_cat) + 1
        cat_ln_end = yaml.index("\n", i_cat) + 1
        yaml = yaml[:cat_ln_start] + categories + yaml[cat_ln_end:]
    else:
        yaml += categories

    # Check thumbnail
    if "image: " in yaml:
        i_image = yaml.index("image: ")

        image_file = yaml[i_image + len("image: ") : yaml.index("\n", i_image)].strip()

        if os.path.exists(j(d(qmd), image_file)):
            yaml = yaml.replace(image_file, j(d(qmd), image_file))
        elif (
            not os.path.exists(image_file)
            and "#" not in yaml[yaml.rindex("\n", 0, i_image) : i_image]
        ):
            yaml = yaml.replace("image: ", "#image: ")

    #### Body ####
    if (
        "eval: false" in yaml
        and "eval: true" not in body
        and "eval=true" not in body
        and "eval= true" not in body
    ):
        continue

    # Check and fix all data paths
    for data_path in data_paths:
        if os.path.exists(data_path):
            continue

        if os.path.exists(new_path := j(d(qmd), data_path)):
            body = body.replace(data_path, new_path)
            print(G, "\tFIXED:", O, data_path + " -> " + new_path)
        elif os.path.exists(new_data := j("data", b(data_path))):
            body = body.replace(data_path, new_data)
            print(G, "\tFIXED:", O, data_path + " -> " + new_path)
        else:
            message = f"Cannot fix {data_path}"
            e_log.append((qmd, message))
            print(R, "\tFAILED:", O, message)

    # Check and fix all pngs?

    # Regex: ^[^\n\r\S]*?```\{(.*?)\}\s*\n(.*?)^[^\n\r\S]*?```
    # Captures all executable code blocks.
    # ^             Start of line
    # [^\n\r\S]*?   Zero or more whitespace (not newline, carriage return or non-whitespace), lazy
    # ```\{         ```{
    # (.*?)         Zero or more characters, lazy. Brackets make this a capturing group (chunk options incl lang)
    # \}            }
    # \s*?\n         Zero or more whitespace, lazy, then a newline
    # (.*?)         Zero or more characters, lazy. Brackets make this a capturing group (the code)
    # ^             Start of line
    # [^\n\r\S]*?   Zero or more whitespace (not newline, carriage return or non-whitespace), lazy
    # ```           ```

    chunks = re.findall(
        r"^[^\n\r\S]*?```\{(.*?)\}\s*\n(.*?)^[^\n\r\S]*?```", body, flags=re.M | re.S
    )

    py_chunks = []
    r_chunks = []

    for ch_options, ch_code in chunks:
        if re.search(r"^\s*#\|\s*eval:\s*false", ch_code, re.M):
            continue

        clean_ops = [
            op.strip().lower() for op in re.split(r"[,\s]", ch_options.strip())
        ]

        if "r" in clean_ops:
            # Extract all library() imports
            packages = re.findall(r"library\s*?\(([\w\s]*?)\)", ch_code)
            bad_packages = {m for m in packages if m not in R_packages}
            if len(bad_packages) > 0:
                message = f"renv.lock does not contain {bad_packages}"
                e_log.append((qmd, message))
                print(R, "\tFAILED:", O, message)
            else:
                r_chunks += [ch_code]

        elif "python" in clean_ops:
            packages = {
                m
                for captures in re.findall(
                    r"^\s*?(import\s+?(\w*)|from\s+?(\w*))", ch_code, re.M
                )
                for m in captures
                if not m.strip().startswith(("import", "from")) and m != ""
            }
            bad_packages = {
                m
                for m in packages
                if m not in py_packages and importlib.util.find_spec(m) == None
            }
            if len(bad_packages) > 0:
                message = f"requirements.txt does not contain {bad_packages}"
                e_log.append((qmd, message))
                print(R, "\tFAILED:", O, message)
            else:
                py_chunks += [ch_code]

        else:
            message = f"Cannot execute code chunk with option(s) '{ch_options}'"
            e_log.append((qmd, message))
            print(R, "\tFAILED:", O, message)

    r_code = "\n".join(r_chunks)
    py_code = "\n".join(py_chunks)

    if r_code != "":
        Rout = run("R -s -e".split() + [r_code], capture_output=True)

        if Rout.returncode != 0:
            message = Rout.stderr
            e_log.append((qmd, message.decode()))
            print(R, "\tFAILED:", O, message)

    if "plotly" in py_code:
        py_code = "import plotly.io as pio\npio.renderers.default = 'svg'\n" + py_code

    if py_code != "":
        e = run_py(py_code)
        if e is not None:
            message = e
            e_log.append((qmd, message))
            print(R, "\tFAILED:", O, message)

    # Overwrite with patches
    with open(qmd, "w") as f:
        f.write(yaml + body)

    #### For render ####
    if qmd not in [error[0] for error in e_log]:
        print(G, "\tSUCCESS", O)
    elif render_list is not None:
        render_list.replace(qmd, "")
        print(R, "\tREMOVED from render list", O)
    else:
        print(R, "\tFAILS TO RENDER", O)

print("The following files fail to render and will not be included in the gallery:")
for file in {error[0] for error in e_log}:
    print(R, file, O)

print("\nWriting to logs and updating quarto inputs.")
with open("_processing/project_errors.log", "w") as f:
    f.write("\n".join(str(item) for item in e_log))

with open("_processing/project_ok.log", "w") as f:
    f.write(
        "\n".join(
            [
                qmd + "," + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for qmd in qmds
                if qmd not in [e[0] for e in e_log]
            ]
        )
    )

if render_list is not None:
    os.environ["QUARTO_PROJECT_INPUT_FILES"] = render_list

# Compare state before and after to remove any created files
new_state_files = {j(path, f) for path, _, fs in os.walk("./") for f in fs}
all_new_files = new_state_files - old_state_files

backups = {path for path in all_new_files if "original_source" in path}
new_files = all_new_files - backups

if not all_new_files:
    print("\nNo new files were created during project testing.")
else:
    if backups:
        print("\nProject testing has created backups of original source files:")

        for file in backups:
            print(file)

        if input("\nWould you like to keep these? [y]/n: ").lower() == "n":
            for file in backups:
                os.remove(file)

    if new_files:
        print("\nProject testing has created new files.")
        for file in new_files:
            print(file)
        if input("\nWould you like to keep these? y/[n]: ").lower() != "y":
            for file in new_files:
                os.remove(file)
