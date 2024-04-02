import os
from shutil import copyfile
import time


def save_file(file: str, data: bytes) -> None:
    with open(file, "wb") as f:
        f.write(data)


def create_folders(path: str) -> None:
    if path != "" and not os.path.exists(path):
        folders = path.split("/")
        path = folders[0]
        for folder in folders[1:]:
            path = f"{path}/{folder}"
            if not os.path.exists(path):
                os.makedirs(path)


def copy_file_to_log_folder(file: str, folder: str) -> None:
    create_folders(folder)
    logtime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
    filename = f"{folder}/{logtime}.jpg"
    copyfile(file, filename)
