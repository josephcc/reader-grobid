"""
Flask app for S2ORC pdf2json utility
"""
import hashlib
from pprint import pprint
import concurrent.futures
from flask_cors import CORS, cross_origin

from flask import Flask, request, jsonify, flash, url_for, redirect, render_template, send_file

from doc2json.grobid2json.process_pdf import process_pdf_stream
from doc2json.tex2json.process_tex import process_tex_stream
from doc2json.jats2json.process_jats import process_jats_stream

from queryS2 import apiGet


app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    return response

ALLOWED_EXTENSIONS = {'pdf', 'gz', 'nxml'}

def convertToScholarPhiFormat(grobid):
    #surveyTitle = grobid['title']
    #print(surveyTitle)
    #query = apiGet('Query', surveyTitle)
    #pprint(query)
    #if len(query['data']) > 0:
    #    print(query['data'][0]['title'])
    #    surveyPaperId = query['data'][0]['paperId']
    #else:
    #    print('Survey paper not found on S2')
    #    surveyPaperId = 'NOT FOUND'

    citations = {}
    allRefs = set()
    for section in grobid['pdf_parse']['body_text']:
        cite_spans = list(filter(lambda span:
            span['ref_id'] and span['ref_id'].startswith('BIBREF') and span['coord']
        , section['cite_spans']))
        if len(cite_spans) == 0:
            continue
        for cite_span in cite_spans:
            # scholarphi pages starts at index 0, but grobid starts at 1
            cite_span['coord']['page'] -= 1 
            ref_id = cite_span['ref_id']

            if not (ref_id in citations):
                allRefs.add(ref_id)
                citations[ref_id] = {
                    'id': ref_id,
                    'type': 'citation',
                    'attributes': {
                        'paper_id': ref_id,
                        'version': 'v1',
                        'source': 's2orc-grobid',
                        'bounding_boxes': [cite_span['coord']],
                        'tags': []
                    }
                }
            else:
                citations[ref_id]['attributes']['bounding_boxes'].append(cite_span['coord'])
    citations = citations.values()
        
    refId2S2 = {}
    bibs = grobid['pdf_parse']['bib_entries']
    def fetch(ref):
        title = bibs[ref]['title']
        query = apiGet('Query', title)
        if len(query.get('data', [])) == 0:
            return None
        query = query['data'][0]
        return query

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        future_to_ref = {executor.submit(fetch, ref): ref for ref in allRefs}
        for future in concurrent.futures.as_completed(future_to_ref):
            ref = future_to_ref[future]
            try:
                data = future.result()
                refId2S2[ref] = data['paperId']
            except Exception as exc:
                print('%r generated an exception: %s' % (ref, exc))
#            else:
#                print('%r page is %d bytes' % (ref, data and len(data) or 0))


    citations = list(filter(lambda citation: citation['id'] in refId2S2, citations))
    for citation in citations:
        s2Id = refId2S2[citation['id']]
        citation['id'] = s2Id
        citation['attributes']['paper_id'] = s2Id

    return {'entities': citations}

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/', methods=['POST'])
@cross_origin()
def upload_file():
    uploaded_file = request.files['file']
    if uploaded_file.filename != '':
        filename = uploaded_file.filename
        # read pdf file
        if filename.endswith('pdf'):
            pdf_stream = uploaded_file.stream
            pdf_content = pdf_stream.read()
            # compute hash
            pdf_sha = hashlib.sha1(pdf_content).hexdigest()
            # get results
            results = process_pdf_stream(filename, pdf_sha, pdf_content)
            results = convertToScholarPhiFormat(results)
            return jsonify(results)
        # read latex file
        elif filename.endswith('gz'):
            zip_stream = uploaded_file.stream
            zip_content = zip_stream.read()
            # get results
            results = process_tex_stream(filename, zip_content)
            results = convertToScholarPhiFormat(results)
            return jsonify(results)
        # read nxml file (jats)
        elif filename.endswith('nxml'):
            xml_stream = uploaded_file.stream
            xml_content = xml_stream.read()
            # get results
            results = process_jats_stream(filename, xml_content)
            results = convertToScholarPhiFormat(results)
            return jsonify(results)
        # unknown
        else:
            return {
                "Error": "Unknown file type!"
            }

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(port=8080, host='0.0.0.0')
