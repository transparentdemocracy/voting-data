"""
Extract info from HTML-formatted voting reports from the Belgian federal chamber's website,
see https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb/recent&language=nl&cfm=/site/wwwcfm/flwb/LastDocument.cfm.
"""
import itertools
import logging
from collections import Counter

from transparentdemocracy.plenaries.extraction import extract_from_html_plenary_reports

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
	proposals, votes, problems = extract_from_html_plenary_reports()

	problems.sort(key=lambda p: p.problem_type)
	problems_by_type = itertools.groupby(problems, lambda p: p.problem_type)

	print("Most common parsing problems:")
	for problem_type, problems in problems_by_type:
		problems = list(problems)
		print(f"{problem_type} -> {len(problems)}:")
		for example_problem in problems:
			print(f"    {example_problem.report_path} - {example_problem.location}")


if __name__ == "__main__":
	main()
