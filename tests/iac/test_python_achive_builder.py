import os
import shutil
import tempfile
import pytest
import sys
from unittest.mock import patch
from zipfile import ZipFile

from api_maker.utils.logger import logger
from api_maker.cloudprints.python_archive_builder import PythonArchiveBuilder

log = logger(__name__)


@pytest.fixture
def working_dir():
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)


@pytest.fixture
def source_file(working_dir):
    source_file = os.path.join(working_dir, "test_source.py")
    with open(source_file, "w") as f:
        f.write("# test file")
    return source_file


def test_prepare_directories(working_dir):
    builder = PythonArchiveBuilder(
        name="test",
        sources={"src": "tests/test_source.py"},
        requirements=[],
        working_dir=working_dir,
    )

    assert os.path.exists(builder._staging)
    assert os.path.exists(builder._libs)
    assert os.path.exists(builder._base_dir)


def test_install_sources(working_dir, source_file):
    builder = PythonArchiveBuilder(
        name="test",
        sources={"src/test_source.py": source_file},
        requirements=[],
        working_dir=working_dir,
    )

    builder.install_sources()
    copied_file = os.path.join(builder._staging, "src/test_source.py")
    assert os.path.exists(copied_file)


def test_write_requirements(working_dir):
    builder = PythonArchiveBuilder(
        name="test",
        sources={},
        requirements=["requests", "boto3", "pyyaml"],
        working_dir=working_dir,
    )

    builder.write_requirements()
    requirements_file = os.path.join(builder._staging, "requirements.txt")
    assert os.path.exists(requirements_file)
    with open(requirements_file, "r") as f:
        lines = f.read().splitlines()
        assert "requests" in lines
        assert "boto3" in lines
        assert "pyyaml" in lines


def test_install_requirements(working_dir):
    builder = PythonArchiveBuilder(
        name="test",
        sources={},
        requirements=["requests", "boto3", "pyyaml"],
        working_dir=working_dir,
    )

    with patch("subprocess.check_call") as mock_check_call:
        builder.install_requirements()
        requirements_file = os.path.join(builder._staging, "requirements.txt")
        mock_check_call.assert_called_with(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-v",
                "--target",
                builder._libs,
                "--platform",
                "manylinux2010_x86_64",
                "--implementation",
                "cp",
                "--only-binary=:all:",
                "--upgrade",
                "--python-version",
                "3.9",
                "-r",
                requirements_file,
            ]
        )


def test_build_archive(working_dir):
    source_file = os.path.join(working_dir, "test_source.py")
    with open(source_file, "w") as f:
        f.write("# test file")

    builder = PythonArchiveBuilder(
        name="test",
        sources={"src/test_source.py": source_file},
        requirements=[],
        working_dir=working_dir,
    )

    builder.build_archive()
    assert os.path.exists(builder._location)
    with ZipFile(builder._location, "r") as zipf:
        assert "src/test_source.py" in zipf.namelist()
        for folder_name, _, filenames in os.walk(builder._libs):
            for filename in filenames:
                lib_file_path = os.path.relpath(
                    os.path.join(folder_name, filename), builder._libs
                )
                assert lib_file_path in zipf.namelist()


def test_hash_comparison(working_dir):
    builder = PythonArchiveBuilder(
        name="test",
        sources={"src": "tests/test_source.py"},
        requirements=[],
        working_dir=working_dir,
    )

    log.info(f"builder.hash: {builder.hash()}")
    assert (
        builder.hash()
        == "3d57a25d98473971cfc17b0ca68376e8adae9b531ae50f0d1d62660d2129e1a0"
    )
