"""Task-related stuff"""

from marshmallow import fields, post_load, Schema
from .custom_fields import _ToodledoDatetime


class DeletedTask:  # pylint: disable=too-few-public-methods
    """Represents a single deleted task returned by GetDeletedTasks"""

    def __init__(self, **data):
        for name, item in data.items():
            setattr(self, name, item)

    def __repr__(self):
        attributes = sorted([f"{name}={item}"
                             for name, item in self.__dict__.items()])
        return f"<Task {', '.join(attributes)}>"


class _DeletedTaskSchema(Schema):
    id_ = fields.Integer(data_key="id")
    stamp = _ToodledoDatetime()

    @post_load
    def _MakeDeletedTask(self, data, many=False, partial=True):
        # I don't know how to handle many yet
        assert not many
        return DeletedTask(**data)
