import os
from shutil import copyfile
import time


def save_file(file: str, data: bytes) -> None:
    """
    Save the given data to the specified file.

    Args:
        file (str): The path of the file to save the data to.
        data (bytes): The data to be saved.

    Returns:
        None
    """
    with open(file, "wb") as f:
        f.write(data)


def create_folders(path: str) -> None:
    """
    Create folders recursively for the given path if they don't already exist.

    Args:
        path (str): The path for which to create the folders.

    Returns:
        None
    """
    if path != "" and not os.path.exists(path):
        folders = path.split("/")
        path = folders[0]
        for folder in folders[1:]:
            path = f"{path}/{folder}"
            if not os.path.exists(path):
                os.makedirs(path)


def copy_file_to_log_folder(file: str, folder: str) -> None:
    """
    Copies a file to the specified log folder.

    Args:
        file (str): The path of the file to be copied.
        folder (str): The path of the log folder.

    Returns:
        None
    """
    create_folders(folder)
    logtime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
    filename = f"{folder}/{logtime}.jpg"
    copyfile(file, filename)
