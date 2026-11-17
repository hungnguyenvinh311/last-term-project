import hashlib
import hmac
import os
import re
import secrets
from Model.application.errors import DomainError

def hash_password(password):
    salt=secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),600000).hex()
    return f'pbkdf2_sha256$600000${salt}${digest}'

def check_password(password,encoded):
    _,iterations,salt,expected=encoded.split('$')
    actual=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),int(iterations)).hex()
    return hmac.compare_digest(actual,expected)

class AccountService:
    def __init__(self,accounts,customers): self.accounts,self.customers=accounts,customers
    def register(self,email,password,fullName):
        return self._register(email,password,fullName,'customer')
    def createStaff(self,email,password,fullName,role='Sales Staff',actorID=None):
        if role not in {'Admin','Sales Staff','Warehouse Staff','Manager'}:
            raise DomainError('Unsupported employee role')
        return self._register(email,password,fullName,role,actorID=actorID)
    def _register(self,email,password,fullName,role,actorID=None):
        email=email.strip().lower();fullName=fullName.strip()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254: raise DomainError('Email không hợp lệ')
        if not 10<=len(password)<=128: raise DomainError('Mật khẩu cần từ 10 đến 128 ký tự')
        if not 1<=len(fullName)<=150: raise DomainError('Tên không hợp lệ')
        return self.accounts.register(email,hash_password(password),fullName,role,actorID=actorID)
    def login(self,email,password):
        account=self.accounts.findByEmail(email.strip().lower())
        # Constant work for an unknown email; never return the account hash.
        dummy='pbkdf2_sha256$600000$demo$'+'0'*64
        valid=check_password(password,account['passwordHash'] if account else dummy)
        if not account or not valid or not account['isActive']: raise DomainError('Email hoặc mật khẩu không đúng',401)
        token=secrets.token_urlsafe(32)
        self.accounts.createSession(hashlib.sha256(token.encode()).hexdigest(),account['accountID'],int(os.getenv('APP_SESSION_HOURS','12')))
        return {'token':token,'account':self.authenticate(token)}
    def authenticate(self,token):
        if not token: raise DomainError('Vui lòng đăng nhập',401)
        account=self.accounts.findSession(hashlib.sha256(token.encode()).hexdigest())
        if not account: raise DomainError('Phiên đăng nhập đã hết hạn',401)
        return account
    def logout(self,token): self.accounts.deleteSession(hashlib.sha256(token.encode()).hexdigest())
    def profile(self,customerID): return self.customers.findById(customerID)
    def updateProfile(self,customerID,values):
        from datetime import date
        phone=str(values.get('phoneNumber','')).strip()
        if phone and not re.fullmatch(r'\+?[0-9 ()-]{8,30}',phone): raise DomainError('Số điện thoại không hợp lệ')
        dob=values.get('dateOfBirth')
        if dob and (dob>date.today() or dob.year<1900): raise DomainError('Ngày sinh không hợp lệ')
        return self.customers.saveContact(customerID,{**values,'phoneNumber':phone})
    def listAccounts(self): return self.accounts.listAccounts()
    def customerHistory(self,accountID): return self.accounts.customerHistory(accountID)
    def setActive(self,accountID,active,actorID): self.accounts.setActive(accountID,active,actorID)
    def setRole(self,accountID,role,actorID): self.accounts.setRole(accountID,role,actorID)
