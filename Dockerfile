FROM python:3.6-alpine
COPY Pipfile.lock /Pipfile.lock
COPY Pipfile /Pipfile
RUN pip install pipenv
RUN pipenv install --system
COPY run.py /app/
COPY ubotvk/ /app/
WORKDIR /app
CMD ["python3", "run.py"]