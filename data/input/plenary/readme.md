# Input files: Plenary reports

This folder is meant for storing plenary reports, as download from the website of the Chamber of the federal government (https://www.dekamer.be).

You can populate this folder by using our download script, or by downloading the plenary reports manually - for example if you want to process only a few plenary reports of your choice.

## Using the download script

Run the following command. You can specify the maximum document number, default is 300

    ./download-reports.sh

## Manual download

Go to [https://www.dekamer.be/kvvcr/showpage.cfm?section=/cricra&language=nl&cfm=dcricra.cfm?type=plen&cricra=cri&count=all](this page) and download all (or some) HTML files. 

We've found the HTML files the easiest to process automatically. 
But you can optionally also download the PDF files, if you'd like to read the plenary reports in a 2-column format.