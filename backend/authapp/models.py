from django.db import models

class Users(models.Model):
    user_id = models.AutoField(primary_key=True, db_column="user_id")
    fname = models.CharField(max_length=100, db_column="fname")
    lname = models.CharField(max_length=100, db_column="lname")
    email = models.EmailField(db_column="email", unique=True)
    username = models.CharField(max_length=100, db_column="username", unique=True)
    passwordhash = models.CharField(max_length=255, db_column="passwordhash")
    role = models.CharField(max_length=50, db_column="role")

    class Meta:
        db_table = '"User"'   # <-- EXACTLY this, with quotes
        managed = False       # existing table; Django won’t try to create/alter
