# Lambda for calling elasticsearch

## preparation

Make sure you have the ES credentials, you'll need to pass them to terraform

Create the lambda layer zip file:

mkdir -p package/python/lib/python3.9/site-packages/
pip install -r requirements.txt package/python/lib/python3.9/site-packages/


## run terraform

tf plan && tf apply

## extra manual step:

create a function url (this should be terraform, but I ran out of play time)

## testing

call the function url directly using <function-url>?q=klimaat&page=5

Note page is 0 based

