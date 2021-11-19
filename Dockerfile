FROM python:3.8.6

WORKDIR /api

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Setup environment - not sure if needed
COPY setup.py .
RUN python setup.py develop

# Copy over the source code
COPY doc2json doc2json/

# Kick things off
ENTRYPOINT [ "python" ]
CMD [ "doc2json/flask/app.py" ]
