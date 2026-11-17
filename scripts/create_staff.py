"""Local administrative command. Credentials are entered privately, never in shell arguments."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from getpass import getpass
from bootstrap import create_app

if __name__=='__main__':
    app=create_app();service=app.state.services['accounts']
    email=input('Staff email: ').strip().lower();name=input('Full name: ').strip()
    password=getpass('Password (10–128 characters): ')
    if len(password)<10 or len(password)>128 or '@' not in email or not name: raise SystemExit('Invalid account details')
    print('Role options: 1 Admin, 2 Sales Staff, 3 Warehouse Staff, 4 Manager')
    selected=input('Role [1]: ').strip() or '1'
    roles={'1':'Admin','2':'Sales Staff','3':'Warehouse Staff','4':'Manager'}
    if selected not in roles: raise SystemExit('Invalid role selection')
    service.createStaff(email,password,name,role=roles[selected])
    print(f"{roles[selected]} account created. No password has been printed or stored in plaintext.")
