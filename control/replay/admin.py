import os
from django.contrib import admin, messages
from django.utils import timezone
import redis
import grpc

from .models import ReplayJob
from . import cdc_pb2
from . import cdc_pb2_grpc

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REPLAYER_HOST = os.getenv("REPLAYER_HOST", "localhost:50051")
REDIS_STREAM = "cdc:events"


@admin.action(description="Run selected replay jobs")
def run_replay_job(modeladmin, request, queryset):
    """
    Admin action that:
    1. Fetches events from Redis for the time range
    2. Sends each event to the gRPC Replayer service
    """
    
    # Connect to Redis
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
    except Exception as e:
        messages.error(request, f"Could not connect to Redis: {e}")
        return
    
    # Connect to gRPC Replayer
    try:
        channel = grpc.insecure_channel(REPLAYER_HOST)
        stub = cdc_pb2_grpc.ReplayerStub(channel)
    except Exception as e:
        messages.error(request, f"Could not connect to Replayer: {e}")
        return
    
    for job in queryset:
        job.status = "running"
        job.save()
        
        try:
            # Convert datetime to millisecond timestamps
            start_ms = int(job.start_time.timestamp() * 1000)
            end_ms = int(job.end_time.timestamp() * 1000)
            
            # Fetch events from Redis Stream in time range
            # Redis Stream IDs are timestamp-based
            events = r.xrange(REDIS_STREAM, min=start_ms, max=end_ms)
            
            count = 0
            for msg_id, data in events:
                payload = data.get(b"payload")
                if not payload:
                    continue
                
                # Deserialize the Protobuf
                record = cdc_pb2.ChangeRecord()
                record.ParseFromString(payload)
                
                # Create replay request
                replay_request = cdc_pb2.ReplayRequest(
                    job_id=str(job.id),
                    event=record,
                    virtual_time=record.commit_time
                )
                
                # Send to Replayer
                response = stub.ReplayEvent(replay_request)
                
                if response.success:
                    count += 1
            
            job.status = "completed"
            job.events_replayed = count
            job.completed_at = timezone.now()
            job.save()
            
            messages.success(request, f"Job {job.id}: Replayed {count} events successfully")
            
        except grpc.RpcError as e:
            job.status = "failed"
            job.error_message = str(e)
            job.save()
            messages.error(request, f"Job {job.id} failed: {e}")
        
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.save()
            messages.error(request, f"Job {job.id} failed: {e}")


@admin.register(ReplayJob)
class ReplayJobAdmin(admin.ModelAdmin):
    list_display = ("id", "start_time", "end_time", "speed_factor", "status", "events_replayed", "created_at")
    list_filter = ("status",)
    readonly_fields = ("status", "events_replayed", "error_message", "created_at", "completed_at")
    actions = [run_replay_job]
    
    fieldsets = (
        ("Time Range", {
            "fields": ("start_time", "end_time", "speed_factor")
        }),
        ("Status", {
            "fields": ("status", "events_replayed", "error_message", "created_at", "completed_at"),
            "classes": ("collapse",)
        }),
    )
