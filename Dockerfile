FROM python:2-onbuild

EXPOSE 5000

ENTRYPOINT ["python", "rest.py"]

