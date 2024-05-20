import re
from collections import defaultdict
from typing import List, Optional

from transparentdemocracy.model import Plenary, DocumentsReference
from transparentdemocracy.plenaries.serialization import load_plenaries


def analyse_document_references():
	plenaries = load_plenaries()

	collected_doc_refs = collect_document_references(plenaries)
	doc_refs_and_locations = dict(
		(lambda d: [(d[k].append(v) or d) for k, v in collected_doc_refs] and d)(defaultdict(list)))

	print(f"{len(doc_refs_and_locations)} unique document references")

	doc_refs = []
	for doc_ref_spec in doc_refs_and_locations.keys():
		result = parse_document_reference(doc_ref_spec)

		doc_refs.append(result)

	bad_refs = [d for d in doc_refs if d.document_reference is None]
	print("Bad references:")
	for bad_ref in bad_refs:
		print(f"   {bad_ref.all_documents_reference}")


def collect_document_references(plenaries: List[Plenary]):
	for plenary in plenaries:
		for discussion in plenary.proposal_discussions:
			for proposal in discussion.proposals:
				if proposal.documents_reference:
					yield proposal.documents_reference, proposal.id
		for motion_group in plenary.motion_groups:
			if motion_group.documents_reference:
				yield motion_group.documents_reference, motion_group.id
			for motion in motion_group.motions:
				if motion.documents_reference:
					yield motion.documents_reference, motion.id


def parse_document_reference(doc_ref_spec: str) -> Optional[DocumentsReference]:
	parts = re.split("[/]", doc_ref_spec)

	if len(parts) > 2:
		return _unparsed(doc_ref_spec)

	try:
		doc_nr = int(parts[0])
	except ValueError as ve:
		return _unparsed(doc_ref_spec)

	if len(parts) == 1:
		sub_doc_refs = []
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
		sub_document_references=sub_doc_refs
	)


def _unparsed(spec):
	return DocumentsReference(
		document_reference=None,
		all_documents_reference=spec,
		main_document_reference=None,
		sub_document_references=[]
	)


def main():
	analyse_document_references()


if __name__ == "__main__":
	main()
