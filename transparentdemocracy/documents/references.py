import re
from typing import Optional

from transparentdemocracy.model import DocumentsReference


def parse_document_reference(doc_ref_spec: str) -> Optional[DocumentsReference]:
	parts = re.split("[/]", doc_ref_spec)

	if len(parts) > 2:
		return _unparsed(doc_ref_spec)

	try:
		doc_nr = int(parts[0])
	except ValueError as ve:
		return _unparsed(doc_ref_spec)

	if len(parts) == 1:
		sub_doc_refs = [1]
	else:
		sub_doc_spec = parts[1]
		sub_doc_refs = [int(part) for part in sub_doc_spec.split("-")]
		if len(sub_doc_refs) > 2:
			print("Invalid sub document spec", sub_doc_spec)

		sub_doc_refs = list(range(sub_doc_refs[0], sub_doc_refs[-1] + 1))

	return DocumentsReference(
		document_reference=doc_nr,
		all_documents_reference=doc_ref_spec,
		main_document_reference=sub_doc_refs[0] if sub_doc_refs else None,
		sub_document_references=sub_doc_refs,
		proposal_discussion_ids=[],
		proposal_ids=[],
		summary_nl="",
		summary_fr=""
	)


def _unparsed(spec):
	return DocumentsReference(
		document_reference=None,
		all_documents_reference=spec,
		main_document_reference=None,
		sub_document_references=[],
		proposal_discussion_ids=[],
		proposal_ids=[],
		summary_nl="",
		summary_fr=""
	)


def main():
	# analyse_document_references()
	# print_subdocument_pdf_urls()
	download_referenced_documents()


if __name__ == "__main__":
	main()
