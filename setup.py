import setuptools

long_description = """#Transparent Democracy"""

with open("requirements.txt", "r") as req_file:
	requirements = req_file.readlines()
setuptools.setup(
	name="transparentdemocracy",
	version="0.0.1",
	author="TODO",
	author_email="TODO@example.com",
	description="Transparent Democracy",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/transparentdemocracy/voting-data",
	packages=setuptools.find_packages(),
	classifiers=[],
	python_requires='>=3.6',
	install_requires=requirements,
	entry_points={
		'console_scripts': [
			'td-plenaries-markdown=transparentdemocracy.plenaries.serialization:write_markdown',
			'td-plenaries-json=transparentdemocracy.plenaries.serialization:write_plenaries_json',
			'td-votes-json=transparentdemocracy.plenaries.serialization:write_votes_json',
			'td-politicians-json=transparentdemocracy.politicians.serialization:create_json',
			'td-print-politicians-by-fraction=transparentdemocracy.politicians.serialization:print_politicians_by_party',
			'td-download-referenced-documents=transparentdemocracy.documents.download:download_referenced_documents',
			'td-summarize=transparentdemocracy.documents.summarize:main',
			'td-fixup-summaries=transparentdemocracy.documents.summarize:fixup_summaries',
			'td-summaries-json=transparentdemocracy.documents.summarize:write_json',
		],
	}
)

