from django.db import models

class Student(models.Model):
    student_id = models.CharField(max_length=20, primary_key=True)  
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    program = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.student_id} - {self.last_name}, {self.first_name}"


class Violation(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='violations')
    type = models.CharField(max_length=100)
    evidence_img1 = models.ImageField(upload_to='violations/', blank=True, null=True)
    evidence_img2 = models.ImageField(upload_to='violations/', blank=True, null=True)
    date_time = models.DateTimeField()
    secu_on_shft = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    
    APPROVAL_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
    ]
    approval = models.CharField(
        max_length=3,
        choices=APPROVAL_CHOICES,
        default='no'
    )
    new_time_of_record = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.student_id} - {self.type} - {self.status}"
