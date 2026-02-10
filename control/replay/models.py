from django.db import models


class ReplayJob(models.Model):
    """A job that replays events from a time range."""
    
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    
    start_time = models.DateTimeField(help_text="Start of time range to replay")
    end_time = models.DateTimeField(help_text="End of time range to replay")
    speed_factor = models.FloatField(default=1.0, help_text="Replay speed (1.0 = real-time, 2.0 = 2x)")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    events_replayed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Job {self.id}: {self.start_time} to {self.end_time} ({self.speed_factor}x)"
    
    class Meta:
        ordering = ["-created_at"]
