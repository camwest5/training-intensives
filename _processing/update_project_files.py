import os

# Go through all qmds in gallery, recursively


def update_data_paths(content: str) -> str:
    for quote in ('"', "'"):
        i = content.find(f".csv{quote}")

        while i != -1:
            data_path_start = content.rfind(quote, 0, i) + 1
            data_path_end = content.find(quote, i)

            old_path = content[data_path_start:data_path_end]

            if os.path.exists(old_path):
                new_path = old_path

            # Check if matches with file in data
            elif any([data_name in old_path for data_name in os.listdir("data")]):
                new_path = os.path.join("data", os.path.basename(old_path))
                content = content.replace(old_path, new_path)
                print(f"REPLACED: {old_path} -> {new_path}")

            else:
                # Try find path relative to file
                new_path = os.path.join(path, old_path)

                if os.path.exists(new_path):
                    content = content.replace(old_path, new_path)
                    print(f"REPLACED: {old_path} -> {new_path}")
                else:
                    print(f"FAILED: {old_path}")

            i = content.find(
                f".csv{quote}", data_path_end + abs(len(new_path) - len(old_path))
            )

    return content


def add_categories(content: str, path: str) -> str:
    # Find end of YAML
    if "listing" not in content:
        # Deterimine tags
        d = os.path.dirname
        b = os.path.basename

        lang = b(d(d(d(path))))
        iteration = b(d(d(path)))
        iteration = "20" + iteration[:2] + " " + iteration[2:]

        # Insert categories
        yaml_start = content.index("---")
        spaces = content[
            content.index("\n", yaml_start) + 1 : content.index("title", yaml_start)
        ]

        yaml_end = content.index("---", yaml_start + 1)

        yaml_insert = f"{spaces}categories: [{lang}, {iteration}]\n"

        if yaml_insert in content:
            content = content.replace(yaml_insert, "")

        content = content[:yaml_end] + yaml_insert + content[yaml_end:]

    return content


def update_date(content: str, path: str) -> str:
    if "listing" not in content:
        d = os.path.dirname
        b = os.path.basename
        iteration = b(d(d(path)))

        if "Summer" in iteration:
            month = "Jan"
        else:
            month = "Jul"

        date = f"{month}-2025"

        yaml_start = content.index("---")
        spaces = content[
            content.index("\n", yaml_start) + 1 : content.index("title", yaml_start)
        ]

        yaml_end = content.index("---", yaml_start + 1)
        yaml_insert = f"{spaces}date: {date}\n"

        # Replace "today" with date, insert date if none

        if "date: " not in content[:yaml_end]:
            content = content[:yaml_end] + yaml_insert + content[yaml_end:]
        elif "today" in content[:yaml_end]:
            content = content[:yaml_end].replace("today", date) + content[yaml_end:]

    return content


for path, dirs, files in os.walk("gallery"):
    qmds = [os.path.join(path, file) for file in files if file.endswith(".qmd")]

    for qmd in qmds:
        with open(qmd) as f:
            content = f.read()

        # Find all .csvs

        content = update_date(content, qmd)

        # Update file
        # with open(qmd, "w") as f:
        #     f.write(content)
