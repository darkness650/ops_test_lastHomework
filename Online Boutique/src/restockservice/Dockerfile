FROM mirror.gcr.io/library/python:3.12-slim

WORKDIR /restockservice

COPY restock_service.py ./

ENV PORT=8080
EXPOSE 8080

CMD ["python", "restock_service.py"]
