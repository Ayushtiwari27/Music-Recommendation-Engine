from django.db import models



class songs(models.Model):
    name=models.CharField(max_length=1000,default="")
    year=models.IntegerField()
    artists=models.TextField(default="")
    

    def __str__(self):
        return self.name
