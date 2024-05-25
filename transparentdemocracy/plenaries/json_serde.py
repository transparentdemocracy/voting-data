#!/usr/bin/env python
import datetime
from json import JSONEncoder

import bs4

from transparentdemocracy.model import ProposalDiscussion, Proposal, MotionGroup, Motion


class PlenaryEncoder(JSONEncoder):
	def default(self, obj):
		if isinstance(obj, bs4.Tag):
			return str(obj)
		if isinstance(obj, ProposalDiscussion):
			return obj.__dict__
		if isinstance(obj, Proposal):
			return obj.__dict__
		if isinstance(obj, MotionGroup):
			return obj.__dict__
		if isinstance(obj, Motion):
			return obj.__dict__
		if isinstance(obj, datetime.date):
			return obj.isoformat()
		if isinstance(obj, str):
			return obj
		return super().default(obj)
