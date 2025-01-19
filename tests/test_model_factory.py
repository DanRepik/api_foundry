# test_model_factory.py

import os
import yaml
import pytest
from api_foundry.utils.logger import logger
from api_foundry.utils.model_factory import ModelFactory
from api_foundry.utils.app_exception import ApplicationException

log = logger(__name__)


@pytest.mark.unit
def test_set_spec():
    # Mock the file content of api_spec.yaml
    model_factory = ModelFactory(
        {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "TestSchema": {
                        "type": "object",
                        "x-af-database": "database",
                        "properties": {
                            "id": {"type": "integer", "x-af-primary-key": "auto"},
                            "name": {"type": "string"},
                        },
                    }
                }
            },
        }
    )

    result = model_factory.get_config_output()
    log.info(f"result: {result}")
    assert result == {
        "schema_objects": {
            "TestSchema": {
                "api_name": "TestSchema",
                "database": "database",
                "table_name": "TestSchema",
                "properties": {
                    "id": {
                        "api_name": "id",
                        "column_name": "id",
                        "api_type": "integer",
                        "column_type": "integer",
                        "required": False,
                        "key_type": "auto",
                    },
                    "name": {
                        "api_name": "name",
                        "column_name": "name",
                        "api_type": "string",
                        "column_type": "string",
                        "required": False,
                    },
                },
                "primary_key": "id",
                "relations": {},
                "permissions": {},
            }
        },
        "path_operations": {},
    }


def test_invalidate_relation():
    # album has the relation of track_items but schema does not include tracks
    log.info("starting test")

    try:
        ModelFactory(
            yaml.safe_load(
                """
components:
  schemas:
    artist:
      type: object
      properties:
        artist_id:
          type: integer
          x-af-primary-key: auto
          description: Unique identifier for the artist.
          example: 1
        name:
          type: string
          maxLength: 120
        album_items:
          type: array
          items:
            $ref: '#/components/schemas/album'
            x-af-child-property: artist_id
          description: List of album items associated with this artist.
      required:
      - artist_id
      x-af-database: chinook
    album:
      type: object
      properties:
        album_id:
          type: integer
          x-af-primary-key: auto
          description: Unique identifier for the album.
          example: 1
        title:
          type: string
          maxLength: 160
        artist_id:
          type: integer
        artist:
          $ref: '#/components/schemas/artist'
          x-af-parent-property: artist_id
          description: Artist associated with the album.
        track_items:
          type: array
          items:
            $ref: '#/components/schemas/track'
            x-af-child-property: album_id
          description: List of track items associated with this album.
      required:
      - album_id
      - title
      - artist_id
      x-af-database: chinook
"""
            )
        )
        assert False
    except KeyError as ke:
        log.info(f"ke: {ke}")
        assert str(ke) == "\"Reference part 'track' not found in the OpenAPI spec.\""


def test_invalid_type():
    # check that property types is checked for valid types

    try:
        ModelFactory(
            yaml.safe_load(
                """
components:
  schemas:
    artist:
      type: object
      properties:
        artist_id:
          type: float
          x-af-primary-key: auto
          description: Unique identifier for the artist.
          example: 1
        name:
          type: string
          maxLength: 120
      required:
      - artist_id
      x-af-database: chinook
"""
            )
        )

    except ApplicationException as ae:
        log.info(f"ae: {ae}")
        assert (
            ae.message
            == "Property: artist_id in schema object: artist of type: float is not a valid type"
        )
        return
    assert False, "Expected exception"


def test_relation():
    # tests object (artist of album) and array (album list of tracks) relations
    log.info("starting test")

    try:
        model_factory = ModelFactory(
            yaml.safe_load(
                """
components:
  schemas:
    artist:
      type: object
      properties:
        artist_id:
          type: integer
          x-af-primary-key: auto
          description: Unique identifier for the artist.
          example: 1
        name:
          type: string
          maxLength: 120
        album_items:
          type: array
          items:
            $ref: '#/components/schemas/album'
            x-af-child-property: artist_id
          description: List of album items associated with this artist.
      required:
      - artist_id
      x-af-database: chinook
    album:
      type: object
      properties:
        album_id:
          type: integer
          x-af-primary-key: auto
          description: Unique identifier for the album.
          example: 1
        title:
          type: string
          maxLength: 160
        artist_id:
          type: integer
        artist:
          $ref: '#/components/schemas/artist'
          x-af-parent-property: artist_id
          description: Artist associated with the album.
      required:
      - album_id
      - title
      - artist_id
      x-af-database: chinook
"""
            )
        )

    except KeyError as ke:
        log.info(f"ke: {ke}")
        assert str(ke) == "\"Reference part 'track' not found in the OpenAPI spec.\""
    result = model_factory.get_config_output()
    log.info(f"result: {result}")
    assert result == {
        "schema_objects": {
            "artist": {
                "api_name": "artist",
                "database": "chinook",
                "table_name": "artist",
                "properties": {
                    "artist_id": {
                        "api_name": "artist_id",
                        "column_name": "artist_id",
                        "api_type": "integer",
                        "column_type": "integer",
                        "required": False,
                        "key_type": "auto",
                    },
                    "name": {
                        "api_name": "name",
                        "column_name": "name",
                        "api_type": "string",
                        "column_type": "string",
                        "required": False,
                        "max_length": 120,
                    },
                },
                "primary_key": "artist_id",
                "relations": {
                    "album_items": {
                        "api_name": "album_items",
                        "api_type": "array",
                        "schema_name": "album",
                        "parent_property": "artist_id",
                    }
                },
                "permissions": {},
            },
            "album": {
                "api_name": "album",
                "database": "chinook",
                "table_name": "album",
                "properties": {
                    "album_id": {
                        "api_name": "album_id",
                        "column_name": "album_id",
                        "api_type": "integer",
                        "column_type": "integer",
                        "required": False,
                        "key_type": "auto",
                    },
                    "title": {
                        "api_name": "title",
                        "column_name": "title",
                        "api_type": "string",
                        "column_type": "string",
                        "required": False,
                        "max_length": 160,
                    },
                    "artist_id": {
                        "api_name": "artist_id",
                        "column_name": "artist_id",
                        "api_type": "integer",
                        "column_type": "integer",
                        "required": False,
                    },
                },
                "primary_key": "album_id",
                "relations": {
                    "artist": {
                        "api_name": "artist",
                        "api_type": "object",
                        "schema_name": "artist",
                        "parent_property": "artist_id",
                    }
                },
                "permissions": {},
            },
        },
        "path_operations": {},
    }


def test_chinook_generation():
    # Define the path to the YAML test spec file
    spec_file_path = os.path.join(os.getcwd(), "resources/chinook_api.yaml")

    try:
        # Load YAML from file
        with open(spec_file_path, "r") as file:
            test_spec = yaml.safe_load(file)

        # Set the specification in the model factory
        model_factory = ModelFactory(test_spec)

        # Get the configuration output
        result = model_factory.get_config_output()
        # log.info(f"result: {result}")

        # Write result to a file in the temp directory
        output_file = os.path.join(os.getcwd(), "resources/api_spec.yaml")
        with open(output_file, "w") as out_file:
            yaml.dump(result, out_file, indent=4)

        # Ensure the result file exists
        assert os.path.exists(output_file)

    except KeyError as ke:
        log.info(f"KeyError: {ke}")
        # Adjust the assertion to match the exact KeyError message
        assert str(ke) == "\"Reference part 'track' not found in the OpenAPI spec.\""
