from glob import glob
import os
from os.path import dirname as d
from os.path import basename as b
from os.path import join as j
from os.path import isfile

import yaml

import project_processing


def find_rendered_files(
    yaml_path: str = "_quarto.yml", exclude_projects: bool = True
) -> set[str]:
    with open(yaml_path) as f:
        proj_yaml = yaml.full_load(f)

    globs = (g + "*" if g.endswith("*") else g for g in proj_yaml["project"]["render"])

    files = {f for g in globs for f in glob(g, recursive=True) if isfile(f)}

    if exclude_projects:
        files = {f for f in files if "gallery" not in f or d(f) == "gallery"}

    return files


def insert_banner(source: str) -> str:
    raise NotImplementedError()


def remove_banner(source: str) -> str:
    raise NotImplementedError()


def process_content() -> None:
    # Determine all rendered files, exclude those in gallery
    qmds = find_rendered_files()

    for qmd in ("./" + f for f in qmds):
        print(project_processing.YLW, "CHECKING:", project_processing.O, qmd)
        with open(qmd) as f:
            content = f.read()

        csv_paths = project_processing.find_paths(content, ".csv")
        png_paths = project_processing.find_paths(content, ".png")
        all_paths = csv_paths | png_paths

        content = project_processing.update_links(qmd, all_paths, content)
        print()

        with open(qmd, "w") as f:
            f.write(content)
    return None


if __name__ == "__main__":
    process_content()
