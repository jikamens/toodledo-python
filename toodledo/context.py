"""Account-related stuff"""
from marshmallow import fields, post_load, Schema

from .custom_fields import _ToodledoBoolean

class Context: # pylint: disable=too-few-public-methods
    """Toodledo context"""
    def __init__(self, **data):
        for name, item in data.items():
            setattr(self, name, item)

    def __repr__(self):
        attributes = sorted([f"{name}={item}" for name, item in self.__dict__.items()])
        return f"<Context {', '.join(attributes)}>"

class _ContextSchema(Schema):
    id_ = fields.Integer(data_key="id")
    name = fields.String()
    private = _ToodledoBoolean()

    @post_load
    def _MakeContext(self, data, many=False, partial=True):
        # I don't know how to handle many yet
        assert not many
        return Context(**data)
