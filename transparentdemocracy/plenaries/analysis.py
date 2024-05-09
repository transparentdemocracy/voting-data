"""
Extract info from HTML-formatted voting reports from the Belgian federal chamber's website,
see https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb/recent&language=nl&cfm=/site/wwwcfm/flwb/LastDocument.cfm.
"""
import collections
import datetime
import glob
import logging
import os
import re
from typing import Tuple, List, Any

from bs4 import BeautifulSoup, NavigableString
from nltk.tokenize import WhitespaceTokenizer
from tqdm.auto import tqdm

from transparentdemocracy import CONFIG
from transparentdemocracy.model import Motion, Plenary, Proposal, ProposalDiscussion, Vote, VoteType, MotionData, \
	BodyTextPart
from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports
from transparentdemocracy.politicians.extraction import Politicians, load_politicians

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DAYS_NL = "maandag,dinsdag,woensdag,donderdag,vrijdag,zaterdag,zondag".split(",")
MONTHS_NL = "januari,februari,maart,april,mei,juni,juli,augustus,september,oktober,november,december".split(",")


def main():
	plenaries, votes = extract_from_html_plenary_reports(CONFIG.plenary_html_input_path("ip100x.html"))

	print(f"# plenaries: {len(plenaries)}")
	print(f"# votes: {len(votes)}")
	print(f"# motions: {sum([len(p.motions) for p in plenaries])}")
	print(f"# motions_datas: {sum([len(p.motion_data) for p in plenaries])}")

	for m in [m for p in plenaries for m in p.motion_data]:
		print(">> MOTION")
		print(m.nl_title)


if __name__ == "__main__":
	main()
