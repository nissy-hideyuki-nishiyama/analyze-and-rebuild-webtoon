import os

class RecursiveTextFileLoader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "directory": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text_list", "filename_list")
    FUNCTION = "load"

    CATEGORY = "text/loaders"

    def load(self, directory):
        texts = []
        filenames = []

        file_list = []

        for root, dirs, files in os.walk(directory):
            for f in files:
                if f.lower().endswith(".txt"):
                    full_path = os.path.join(root, f)
                    rel_dir = os.path.relpath(root, directory)
                    file_list.append((rel_dir, f, full_path))

        file_list.sort(key=lambda x: (x[0], x[1]))

        for rel_dir, fname, full_path in file_list:
            with open(full_path, "r", encoding="utf-8") as fp:
                texts.append(fp.read())
                filenames.append(os.path.join(rel_dir, fname))

        return (texts, filenames)


NODE_CLASS_MAPPINGS = {
    "RecursiveTextFileLoader": RecursiveTextFileLoader
}
