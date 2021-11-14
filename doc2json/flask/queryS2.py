import requests
from secrets import APIKEY

BASEURL = 'partner.semanticscholar.org'
HEADERS = {'X-API-KEY': APIKEY}

# doc: https://api.semanticscholar.org/graph/v1#operation/get_graph_get_paper_citations
ENDPOINTS = {
    'Query': 'https://{}/graph/v1/paper/search?query=%s&limit=1&fields=title,abstract'.format(BASEURL),
    'Details': 'https://{}/graph/v1/paper/%s?fields=title,citations.authors,abstract'.format(BASEURL),
    'Citations': 'https://{}/graph/v1/paper/%s/citations?fields=contexts,intents,isInfluential,paperId,title,year&limit=1000'.format(BASEURL),
    'References': 'https://{}/graph/v1/paper/%s/references?fields=contexts,intents,isInfluential,paperId,title,year'.format(BASEURL)
}

def apiGet(endpoint, payload):
    return requests.get(url=ENDPOINTS[endpoint] % payload, headers=HEADERS).json()
