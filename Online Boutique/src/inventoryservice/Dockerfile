FROM python:3.12-slim

WORKDIR /inventoryservice

COPY inventory_service.py inventory.json ./

ENV PORT=8080
EXPOSE 8080

CMD ["python", "inventory_service.py"]
