#!/usr/bin/env python
import datetime
from json import JSONEncoder



class DateTimeEncoder(JSONEncoder):
	def default(self, obj):
		if isinstance(obj, datetime.date):
			return obj.isoformat()
		else:
			return obj.__dict__
