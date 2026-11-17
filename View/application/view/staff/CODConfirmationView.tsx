import {api,post} from '../../api';
import type {Feedback} from '../StaffView';
export function CODConfirmationView({order,done,fail,notify}:Feedback&{order:any;done:()=>void}){
 if(order.paymentMethod!=='COD'||order.status!=='Delivered'||order.payment?.status!=='UnpaidCOD')return null;
 return <form onSubmit={async e=>{e.preventDefault();try{const d=Object.fromEntries(new FormData(e.currentTarget));await api('/staff/orders/'+order.orderID+'/cod-confirmation',post(d));notify('Đã xác nhận thu COD mô phỏng');done()}catch(e){fail((e as Error).message)}}}><h3>Xác nhận thu COD mô phỏng</h3><label>Số tiền đã thu<input name="amount" type="number" step="0.01" min={0} required defaultValue={order.totalAmount}/></label><label>Mã vận đơn<input name="trackingNumber" required defaultValue={order.shipment?.trackingNumber} maxLength={100}/></label><label>Mã xác nhận duy nhất<input name="reference" required minLength={3} maxLength={100} pattern="[A-Za-z0-9_-]+" placeholder={'COD-'+order.orderID}/></label><button>Xác nhận COD</button></form>;
}
