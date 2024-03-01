
class SchemaModel:
  def __init__(self, schema) -> None:
    self.schema = schema

  def get_schema(self) -> str:
    return self.schema.get("x-schema")

  def get_engine(self) -> str:
    return self.schema.get("x-engine")
