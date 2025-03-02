# Lambda for calling elasticsearch

## preparation

Make sure you have the ES credentials, you'll need to pass them to terraform

## run terraform

export AWS_PROFILE=wddp #change this if yours is named differently
export TF_VAR_es_auth=<ES_AUTH>

tf plan
tf apply

## testing

    GET_MOTION=$(tf output -json function_url|jq -r '.get_motion')
    SEARCH_MOTIONS=$(tf output -json function_url|jq -r '.search_motions')
    SEARCH_PLENARIES=$(tf output -json function_url|jq -r '.search_plenaries')

    curl ${GET_MOTION}55_071_mg_22
    curl ${SEARCH_MOTIONS}
    curl ${SEARCH_MOTIONS}?q=klimaat&page=0
    curl ${SEARCH_PLENARIES}
    curl ${SEARCH_PLENARIES}?q=klimaat&page=0

