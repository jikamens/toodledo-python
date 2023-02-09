"""Task-related stuff"""

from marshmallow import fields, post_load, Schema
from marshmallow.validate import Length

from .custom_fields import (
    _ToodledoBoolean,
    _ToodledoDate,
    _ToodledoDatetime,
    _ToodledoDueDateModifier,
    _ToodledoListId,
    _ToodledoPriority,
    _ToodledoStatus,
    _ToodledoTags,
    _ToodledoInteger,
)


class Task:
    """Represents a single task"""

    def __init__(self, **data):
        for name, item in data.items():
            setattr(self, name, item)

    def __repr__(self):
        attributes = sorted([f"{name}={item}"
                             for name, item in self.__dict__.items()])
        return f"<Task {', '.join(attributes)}>"

    def IsComplete(self):
        """Indicate whether this task is complete"""
        return self.completedDate is not None  # pylint: disable=no-member


class _TaskSchema(Schema):
    id_ = fields.Integer(data_key="id")
    title = fields.String(validate=Length(max=255))
    tags = _ToodledoTags(data_key="tag")
    startDate = _ToodledoDate(data_key="startdate")
    dueDate = _ToodledoDate(data_key="duedate")
    dueTime = _ToodledoDatetime(data_key="duetime")
    modified = _ToodledoDatetime()
    completedDate = _ToodledoDate(data_key="completed")
    star = _ToodledoBoolean()
    priority = _ToodledoPriority()
    dueDateModifier = _ToodledoDueDateModifier(data_key="duedatemod")
    status = _ToodledoStatus()
    length = fields.Integer()
    note = fields.String()
    repeat = fields.String()
    parent = _ToodledoInteger()
    folderId = _ToodledoListId(data_key="folder")
    contextId = _ToodledoListId(data_key="context")
    meta = fields.String(allow_none=True)
    reschedule = fields.Integer()
    # Note: This is an internal field that the API isn't supposed to be
    # returning. You should ignore it. It's included here only to maintain
    # schema validation.
    repeatfrom = fields.Integer(allow_none=True)

    @post_load
    def _MakeTask(self, data, many=False, partial=True):
        # I don't know how to handle many yet
        assert not many
        return Task(**data)


def _DumpTaskList(taskList):
    # TODO - pass many=True to the schema instead of this custom stuff
    schema = _TaskSchema()
    return [schema.dump(task) for task in taskList]
