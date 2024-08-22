import hashlib
import os
import re

from api_foundry.utils.logger import logger, DEBUG

log = logger(__name__)


class HashComparator:
    def __init__(self, hash_algorithm="sha256"):
        self.hash_algorithm = hash_algorithm

    def check_folder(self, hash_file: str, hash_dir: str):
        old_hash = self.read(hash_file)
        log.info(f"old_hash: {old_hash}")
        if old_hash is None:
            return False

        new_hash = self.hash_folder(hash_dir)
        log.info(f"new_hash: {new_hash}")
        return self.compare(old_hash, new_hash)

    def hash_file(self, file_path):
        """
        Calculate the hash value of a file.
        """
        hasher = hashlib.new(self.hash_algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def hash_folder(self, folder_path, include_regex=None, exclude_regex=None):
        hasher = hashlib.new(self.hash_algorithm)

        include_pattern = re.compile(include_regex) if include_regex else None
        exclude_pattern = re.compile(exclude_regex) if exclude_regex else None

        for root, dirs, files in os.walk(folder_path):
            for file in sorted(files):
                file_path = os.path.join(root, file)

                # Check if the file should be included
                if include_pattern and not include_pattern.match(file):
                    continue

                # Check if the file should be excluded
                if exclude_pattern and exclude_pattern.match(file):
                    continue

                with open(file_path, "rb") as f:
                    # Update the folder hash with the hash of the file contents
                    file_hash = hashlib.sha256()
                    file_hash.update(f.read())
                    hasher.update(file_hash.digest())

        return hasher.hexdigest()

    def read(self, file_path):
        """
        Read the hash value from a file.
        """
        if log.isEnabledFor(DEBUG):
            log.debug(f"reading hash: {file_path}")

        if not os.path.exists(file_path):
            return None
        try:
            with open(os.path.join(file_path, ".hash"), "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            log.debug(f"hash file not found: {file_path}")
            return None

    def write(self, hash_value, file_path):
        """
        Write the hash value to a file.
        """
        if log.isEnabledFor(DEBUG):
            log.debug(f"writing hash: {file_path}")

        with open(os.path.join(file_path, ".hash"), "w") as f:
            f.write(hash_value)

    def compare(self, hash_value1, hash_value2):
        """
        Compare two hash values.
        """
        return False if hash_value1 is None else hash_value1 == hash_value2
