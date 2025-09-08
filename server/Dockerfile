FROM python:3.11-slim-buster


WORKDIR /app


COPY requirements.txt .

RUN pip3 install --upgrade pip

RUN pip3 install  --upgrade setuptools

RUN pip3 install  --upgrade futures

RUN pip3 install --no-cache-dir -r requirements.txt


COPY . .

CMD ["python", "app.py"]