import json
import os
import shutil
import subprocess
import sys
from zipfile import ZipFile

from api_maker.utils.logger import logger, DEBUG
from .hash_comparator import HashComparator
from .archive_builder import ArchiveBuilder

log = logger(__name__)


class PythonArchiveBuilder(ArchiveBuilder):
    _hash: str
    _location: str

    def __init__(
        self,
        name: str,
        *,
        sources: dict[str, str],
        requirements: list[str],
        working_dir: str,
    ):
        self.name = name
        self._sources = sources
        self._requirements = requirements
        self._working_dir = working_dir

        self.prepare()

        hash_comparator = HashComparator()
        new_hash = hash_comparator.hash_folder(self._staging)
        old_hash = hash_comparator.read(self._base_dir)
        log.debug(f"old_hash: {old_hash}, new_hash: {new_hash}")
        if old_hash == new_hash:
            self._hash = old_hash or ""
        else:
            self.install_requirements()
            self.build_archive()
            self._hash = new_hash
            hash_comparator.write(self._hash, self._base_dir)
    
    def hash(self) -> str:
        return self._hash

    def location(self) -> str:
        return self._location

    def prepare(self):
        self._base_dir = os.path.join(self._working_dir, f"{self.name}-lambda")
        self._staging = os.path.join(self._base_dir, "staging")
        if os.path.exists(self._staging):
            self.clean_folder(self._staging)
        else:
            os.makedirs(self._staging)

        self._libs = os.path.join(self._base_dir, "libs")
        if os.path.exists(self._libs):
            self.clean_folder(self._libs)
        else:
            os.makedirs(self._libs)

        self._location = os.path.join(self._base_dir, f"{self.name}.zip")
        self.install_sources()
        self.write_requirements()

    def build_archive(self):
        log.info(f"building archive: {self.name}")
        # Create a ZIP archive of the Lambda function code and requirements
        with ZipFile(self._location, "w") as zipf:
            for top_folder in [self._staging, self._libs]:
                for folder_name, _, filenames in os.walk(top_folder):
                    for filename in filenames:
                        file_path = os.path.join(folder_name, filename)
                        archive_path = os.path.join(
                            os.path.relpath(folder_name, top_folder), filename
                        )
                        zipf.write(file_path, archive_path)

    def install_sources(self):
        log.info(f"installing resources: {self.name}")
        if self._sources is None:
            return
        for destination, source_folder in self._sources.items():
            # Copy the entire contents of the source folder
            # to the destination folder
            destination_folder = os.path.join(self._staging, destination)
            log.info(
                f"source: {source_folder}, destination: {destination_folder}"
            )
            shutil.copytree(source_folder, destination_folder)
            log.info(
                f"Folder copied from {source_folder} to {destination_folder}"
            )

    def write_requirements(self):
        if log.isEnabledFor(DEBUG):
            log.debug("writing requirements")

        with open(f"{self._staging}/requirements.txt", "w") as f:
            for requirement in self._requirements:
                f.write(requirement + "\n")

    def install_requirements(self):
        log.info(f"installing packages {self.name}")
        self.clean_folder(self._libs)
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--target",
                self._libs,
                "--platform",
                "manylinux2010_x86_64",
                "--implementation",
                "cp",
                "--only-binary=:all:",
                "--upgrade",
                "--python-version",
                "3.9",
                "-r",
                os.path.join(self._staging, "requirements.txt"),
            ]
        )

    def clean_folder(self, folder_path):
        """
        Remove all files and folders from the specified folder.

        Args:
            folder_path (str): Path to the folder from which to
              remove files and folders.

        Returns:
            None
        """
        log.info(f"Cleaning folder: {folder_path}")
        # Remove all files and subdirectories in the specified folder
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        log.info(f"All files and folders removed from {folder_path}")


