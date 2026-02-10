import grpc
from concurrent import futures
import time

import cdc_pb2
import cdc_pb2_grpc


class ReplayerService(cdc_pb2_grpc.ReplayerServicer):
    """
    gRPC service that receives replay requests.
    In a real system, this would write to a target database.
    """
    
    def ReplayEvent(self, request, context):
        job_id = request.job_id
        event = request.event
        virtual_time = request.virtual_time
        
        print(f"[Replayer] Job {job_id}: {event.operation} on {event.table}")
        print(f"           LSN: {event.lsn}")
        print(f"           Virtual time: {virtual_time}")
        print(f"           Data: {event.raw_data[:50]}...")
        
        # Simulate processing time
        time.sleep(0.05)
        
        # In a real system, you would:
        # - Parse the raw_data
        # - Execute the INSERT/UPDATE/DELETE on target DB
        # - Handle conflicts and errors
        
        return cdc_pb2.ReplayResponse(
            success=True,
            message=f"Replayed {event.operation} on {event.table}"
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cdc_pb2_grpc.add_ReplayerServicer_to_server(ReplayerService(), server)
    
    server.add_insecure_port('[::]:50051')
    print("Replayer gRPC server started on port 50051")
    
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
