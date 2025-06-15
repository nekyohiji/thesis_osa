from django.db import models

class Student(models.Model):
    tupc_id = models.CharField(max_length=50, unique=True)
    program = models.CharField(max_length=50)
    last_name = models.CharField(max_length=128)
    first_name = models.CharField(max_length=128)
    middle_initial = models.CharField(max_length=5, blank=True, null=True)
    extension = models.CharField(max_length=10, blank=True, null=True)
    email = models.EmailField(unique=True)
    
    class Meta:
        db_table = 'student_record'

    def __str__(self):
        return f"{self.tupc_id} - {self.last_name}, {self.first_name}"
