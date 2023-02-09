"""Account-related stuff"""
from marshmallow import fields, post_load, Schema

from .custom_fields import _ToodledoBoolean, _ToodledoDatetime

class _Account: # pylint: disable=too-few-public-methods
    def __init__(self, lastEditTask, lastDeleteTask):
        self.lastEditTask = lastEditTask
        self.lastDeleteTask = lastDeleteTask

    def __repr__(self):
        return f"<_Account lastEditTask={self.lastEditTask}, lastDeleteTask={self.lastDeleteTask}>"

class _AccountSchema(Schema):
    userid = fields.String()
    alias = fields.String()
    email = fields.String()
    pro = fields.Integer()
    dateFormat = fields.Integer(data_key="dateformat")
    timezone = fields.Integer()
    hideMonths = fields.Integer(data_key="hidemonths")
    hotListPriority = fields.Integer(data_key="hotlistpriority")
    hotListDueDate = fields.Integer(data_key="hotlistduedate")
    hotListStar = fields.Integer(data_key="hotliststar")
    hotListStatus = fields.Integer(data_key="hotliststatus")
    showTabNums = _ToodledoBoolean(data_key="showtabnums")
    lastEditTask = _ToodledoDatetime(data_key="lastedit_task")
    lastDeleteTask = _ToodledoDatetime(data_key="lastdelete_task")
    lastEditFolder = _ToodledoDatetime(data_key="lastedit_folder")
    lastEditContext = _ToodledoDatetime(data_key="lastedit_context")
    lastEditGoial = _ToodledoDatetime(data_key="lastedit_goal")
    lastEditLocation = _ToodledoDatetime(data_key="lastedit_location")
    lastEditNote = _ToodledoDatetime(data_key="lastedit_note")
    lastDeleteNote = _ToodledoDatetime(data_key="lastdelete_note")
    lastEditList = _ToodledoDatetime(data_key="lastedit_list")
    lastEditOutline = _ToodledoDatetime(data_key="lastedit_outline")

    @post_load
    def _MakeAccount(self, data, many=False, partial=True):
        # I don't know how to handle many yet
        assert not many
        return _Account(data["lastEditTask"], data["lastDeleteTask"])
