# syntax=docker/dockerfile:1
FROM python:3.10.9-bullseye
WORKDIR /python-docker
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD export API_KEY=pk_cd773363c72f4956b4ea7b2ff2c76c71  &&  [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
