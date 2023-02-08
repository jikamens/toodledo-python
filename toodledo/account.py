"""Account-related stuff"""
from marshmallow import post_load, Schema

from .custom_fields import _ToodledoDatetime

class _Account: # pylint: disable=too-few-public-methods
	def __init__(self, lastEditTask, lastDeleteTask):
		self.lastEditTask = lastEditTask
		self.lastDeleteTask = lastDeleteTask

	def __repr__(self):
		return "<_Account lastEditTask={}, lastDeleteTask={}>".format(self.lastEditTask, self.lastDeleteTask)

class _AccountSchema(Schema):
	lastEditTask = _ToodledoDatetime(data_key="lastedit_task")
	lastDeleteTask = _ToodledoDatetime(data_key="lastdelete_task")

	@post_load
	def _MakeAccount(self, data, many=False, partial=True): # pylint: disable=no-self-use
		# I don't know how to handle many yet
		assert not many
		return _Account(data["lastEditTask"], data["lastDeleteTask"])
