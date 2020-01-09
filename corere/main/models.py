from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    pass
    # __tablename__ = 'users'
    # id = Column(Integer, primary_key=True)
    # email = Column(String(250), nullable=False, unique=True)
    # given_name = Column(String(250))
    # family_name = Column(String(250))
    # role = Column(Integer)

    # #catalogs = relationship("catalog", backref="user")

    # def __repr__(self):
    #     return '["{}","{}","{}","{}","{}"]'.format(self.id,self.email,self.given_name,self.family_name,self.role)
    # email = models.EmailField(max_length=254)
    # given_name = models.CharField(max_length=200)
    # family_name = models.CharField(max_length=200)
    
class Catalog(models.Model):
    #__tablename__ = 'catalog'
    
    user_id = models.ForeignKey('User', on_delete=models.SET_NULL, null=True) #Do we want orphans?
    status = models.CharField(max_length=250, default="Draft")
    status2 = models.CharField(max_length=250)
    title = models.CharField(max_length=250)
    number = models.CharField(max_length=250)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    collection = models.BooleanField( null=True)
    publish_r = models.BooleanField( default=False)
    publish_a = models.BooleanField( default=False)
    published = models.BooleanField( default=False)
    archive = models.BooleanField( default=False)


    def __repr__(self):
        return '["{}","{}","{}","{}","{}","{}","{}"."{}","{}","{}","{}","{}","{}"]'.format(self.id,self.user_id,self.status,self.status2, self.title, self.number,
        self.created, self.updated, self.collection, self.publish_r, self.publish_a, self.published, self.archive)
