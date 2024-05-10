"""
Extract info from HTML-formatted voting reports from the Belgian federal chamber's website,
see https://www.dekamer.be/kvvcr/showpage.cfm?section=/flwb/recent&language=nl&cfm=/site/wwwcfm/flwb/LastDocument.cfm.
"""
import logging

from transparentdemocracy import CONFIG
from transparentdemocracy.plenaries.extraction import _read_plenary_html, \
	_extract_motion_report_items

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
	report_path = CONFIG.plenary_html_input_path("ip271x.html")
	motion_report_items = _extract_motion_report_items(report_path, _read_plenary_html(report_path))

	print(f"# motion report items: {len(motion_report_items)}")

	for m in motion_report_items:
		num_nl_title_tags = len(m.nl_title_tags)
		num_fr_title_tags = len(m.fr_title_tags)
		num_body_text_parts = len(m.body_text_parts)

		print(f"Motion {m.label} / nl {num_nl_title_tags} / fr {num_fr_title_tags} / body {num_body_text_parts}")
		# print(f"NL: {m.nl_title}")
		# print(f"FR: {m.fr_title}")
		# print("\n".join([el.text[:20] for el in m.body]))


if __name__ == "__main__":
	main()
