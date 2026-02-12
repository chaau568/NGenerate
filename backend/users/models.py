from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):    
    username = models.CharField(max_length=255, unique=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )
    STATUS_CHOICES = (
        ('activate', 'Activate'),
        ('deleted', 'Deleted'),
        ('suspended', 'Suspended'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='activate')
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    
    def soft_delete(self):
        self.status = 'deleted'
        self.is_active = False
        
        # clear personal information
        self.email = None
        self.password = None
        # อื่นๆ 
        
        self.save()
        
        # สั่งลบข้อมูลที่ผูกไว้ (ที่มี on_delete=models.CASCADE)
        # self.novels.all().delete()
        # self.analysis_session.all().delete()
        
