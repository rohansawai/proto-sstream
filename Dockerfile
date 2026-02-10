FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. proto/cdc.proto

RUN cp cdc_pb2.py control/replay/ && cp cdc_pb2_grpc.py control/replay/

RUN sed -i 's/import cdc_pb2 as cdc__pb2/from . import cdc_pb2 as cdc__pb2/' control/replay/cdc_pb2_grpc.py

CMD ["python", "ingestor.py"]
