from fastapi import Request
from Model.application.errors import DomainError

def bearer(request):
    value=request.headers.get('authorization','')
    return value[7:] if value.startswith('Bearer ') else ''

def identity(request,accounts,optional=False,staff=False,roles=None):
    token=bearer(request)
    if optional and not token: return None
    user=accounts.authenticate(token)
    if staff and user['role'] in {'customer','Customer'}: raise DomainError('Only employees may access this function',403)
    if roles is not None and user.get('role') not in set(roles):
        raise DomainError('Your account role is not allowed to perform this action',403)
    return user

async def read_upload(file,maximum):
    from Model.application.errors import DomainError
    content=await file.read(maximum+1)
    if len(content)>maximum: raise DomainError('Tệp vượt quá dung lượng cho phép',413)
    return content
