"""
Extract info from HTML-formatted voting reports from the Belgian federal chamber's website,
see https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb/recent&language=nl&cfm=/site/wwwcfm/flwb/LastDocument.cfm.
"""
import logging
from collections import Counter

from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
	proposals, votes, problems = extract_from_html_plenary_reports()

	counter = Counter([problem.problem_type for problem in problems])

	print("Most common parsing problems:")
	for problem_type, count in counter.most_common(10):
		print(f"{problem_type} -> {count}")


if __name__ == "__main__":
	main()
