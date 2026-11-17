from collections import defaultdict,deque
from datetime import date
from threading import Lock
from time import monotonic
from fastapi import APIRouter,Request
from pydantic import BaseModel,Field
from Model.application.errors import DomainError
from .security import identity,bearer
from Model.application.contract.IAccount import IAccount

class Credentials(BaseModel):
    email:str=Field(max_length=254)
    password:str=Field(min_length=1,max_length=128)
class Registration(Credentials):
    fullName:str=Field(min_length=1,max_length=150)
class Profile(BaseModel):
    dateOfBirth:date|None=None
    fullName:str=Field(min_length=1,max_length=150)
    phoneNumber:str=Field(default='',max_length=30)

class AccountController:
    def __init__(self,service:IAccount):
        self.router=APIRouter(prefix='/api/accounts',tags=['Accounts']);r=self.router
        attempts=defaultdict(deque);lock=Lock()
        def throttle(request):
            ip=request.client.host if request.client else 'local';now=monotonic()
            with lock:
                if len(attempts)>1000: attempts.clear()
                q=attempts[ip]
                while q and now-q[0]>60:q.popleft()
                if len(q)>=15:raise DomainError('Thử quá nhiều lần. Vui lòng đợi một phút.',429)
                q.append(now)
        @r.post('/register',status_code=201)
        def register(body:Registration,request:Request):
            throttle(request);return service.register(body.email,body.password,body.fullName)
        @r.post('/login')
        def login(body:Credentials,request:Request):
            throttle(request);return service.login(body.email,body.password)
        @r.post('/logout')
        def logout(request:Request):
            identity(request,service);service.logout(bearer(request));return {'ok':True}
        @r.get('/me')
        def me(request:Request):
            user=identity(request,service)
            return {'account':user,'profile':service.profile(user['customerID']) if user.get('customerID') else None}
        @r.put('/me')
        def profile(body:Profile,request:Request):
            user=identity(request,service)
            if not user.get('customerID'):
                raise DomainError('Only customers have an editable customer profile',403)
            return service.updateProfile(user['customerID'],body.model_dump(exclude_unset=True))
