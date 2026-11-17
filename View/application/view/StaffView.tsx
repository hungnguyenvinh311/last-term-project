import {useState} from 'react';
import {CatalogAdminView} from './staff/CatalogAdminView';
import {AccountAdminView} from './staff/AccountAdminView';
import {SalesOrdersView} from './staff/SalesOrdersView';
import {ReportsView} from './staff/ReportsView';
import {InventoryView} from './staff/InventoryView';

export type EmployeeRole='Admin'|'Sales Staff'|'Warehouse Staff'|'Manager';
export type Feedback={fail:(s:string)=>void;notify:(s:string)=>void};

export function StaffView({role,fail,notify}:{role:EmployeeRole}&Feedback){
 const allowed=role==='Admin'?['orders','inventory','catalogue','accounts','reports']:
  role==='Sales Staff'?['orders']:
  role==='Warehouse Staff'?['orders','inventory']:
  ['reports'];
 const labels:Record<string,string>={orders:'Đơn hàng',inventory:'Kho hàng',catalogue:'Sản phẩm và danh mục',accounts:'Tài khoản',reports:'Báo cáo'};
 const [tab,setTab]=useState(allowed[0]);
 return <section className="panel"><p className="eyebrow">STAFF WORKSPACE · {role.toUpperCase()}</p><h1>Không gian làm việc</h1>
  <div className="staff-tabs">{allowed.map(id=><button key={id} className={tab===id?'primary':''} onClick={()=>setTab(id)}>{labels[id]}</button>)}</div>
  {tab==='orders'&&<SalesOrdersView role={role} fail={fail} notify={notify}/>}
  {tab==='inventory'&&<InventoryView fail={fail} notify={notify}/>}
  {tab==='catalogue'&&<CatalogAdminView fail={fail} notify={notify}/>}
  {tab==='accounts'&&<AccountAdminView fail={fail} notify={notify}/>}
  {tab==='reports'&&<ReportsView fail={fail} notify={notify}/>}
 </section>;
}
