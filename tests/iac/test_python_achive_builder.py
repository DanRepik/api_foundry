import os
import shutil
import subprocess
import tempfile
import pytest
import sys
from unittest.mock import patch, MagicMock
from zipfile import ZipFile

from api_maker.cloudprints.python_archive_builder import PythonArchiveBuilder


@pytest.fixture
def mock_hash_comparator():
    with patch('your_module.HashComparator') as MockHashComparator:
        mock_instance = MockHashComparator.return_value
        mock_instance.hash_folder.return_value = 'new_hash'
        mock_instance.read.return_value = 'old_hash'
        yield mock_instance


@pytest.fixture
def working_dir():
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)


def test_prepare_directories(working_dir):
    builder = PythonArchiveBuilder(
        name='test',
        sources={'src': 'tests/test_source.py'},
        requirements=[],
        working_dir=working_dir
    )

    assert os.path.exists(builder._staging)
    assert os.path.exists(builder._libs)
    assert os.path.exists(builder._base_dir)


def test_install_sources(working_dir):
    source_file = os.path.join(working_dir, 'test_source.py')
    with open(source_file, 'w') as f:
        f.write("# test file")

    builder = PythonArchiveBuilder(
        name='test',
        sources={'src/test_source.py': source_file},
        requirements=[],
        working_dir=working_dir
    )

    builder.install_sources()
    copied_file = os.path.join(builder._staging, 'src/test_source.py')
    assert os.path.exists(copied_file)


def test_write_requirements(working_dir):
    builder = PythonArchiveBuilder(
        name='test',
        sources={},
        requirements=['requests', 'boto3', 'pyyaml'],
        working_dir=working_dir
    )

    builder.write_requirements()
    requirements_file = os.path.join(builder._staging, 'requirements.txt')
    assert os.path.exists(requirements_file)
    with open(requirements_file, 'r') as f:
        lines = f.read().splitlines()
        assert 'requests' in lines
        assert 'boto3' in lines
        assert 'pyyaml' in lines


def test_install_requirements(working_dir):
    builder = PythonArchiveBuilder(
        name='test',
        sources={},
        requirements=['requests', 'boto3', 'pyyaml'],
        working_dir=working_dir
    )

    with patch('subprocess.check_call') as mock_check_call:
        builder.install_requirements()
        requirements_file = os.path.join(builder._staging, 'requirements.txt')
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
    source_file = os.path.join(working_dir, 'test_source.py')
    with open(source_file, 'w') as f:
        f.write("# test file")

    builder = PythonArchiveBuilder(
        name='test',
        sources={'src/test_source.py': source_file},
        requirements=[],
        working_dir=working_dir
    )

    builder.build_archive()
    assert os.path.exists(builder._location)
    with ZipFile(builder._location, 'r') as zipf:
        assert 'src/test_source.py' in zipf.namelist()
        for folder_name, _, filenames in os.walk(builder._libs):
            for filename in filenames:
                lib_file_path = os.path.relpath(os.path.join(folder_name, filename), builder._libs)
                assert lib_file_path in zipf.namelist()


def test_hash_comparison(mock_hash_comparator, working_dir):
    builder = PythonArchiveBuilder(
        name='test',
        sources={'src': 'tests/test_source.py'},
        requirements=[],
        working_dir=working_dir
    )

    assert builder.hash() == 'new_hash'
    mock_hash_comparator.hash_folder.assert_called_once_with(builder._staging)
    mock_hash_comparator.read.assert_called_once_with(builder._base_dir)
    mock_hash_comparator.write.assert_called_once_with('new_hash', builder._base_dir)
