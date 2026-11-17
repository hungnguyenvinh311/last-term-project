import {api} from '../../api';
import type {Feedback} from '../StaffView';
export function FulfilmentView({order,done,fail,notify}:Feedback&{order:any;done:()=>void}){
 const next:Record<string,[string,string]>={Confirmed:['Packing','Bắt đầu đóng gói'],Packing:['Packed','Hoàn tất đóng gói'],Packed:['Dispatched','Xuất giao']};
 const step=next[order.status];
 return <><p>Vận đơn: {order.shipment?.trackingNumber||'Chưa tạo'} · {order.shipment?.carrier||'—'} · {order.shipment?.status||'—'}</p><p>Ngày giao: {order.shipment?.deliveredAt||'Chưa giao'}</p>{order.status==='Dispatched'&&<p>Đã xuất giao. Đang chờ khách hàng xác nhận đã nhận hàng.</p>}{step&&<button onClick={async()=>{try{await api('/staff/orders/'+order.orderID+'/shipment',{method:'PUT',body:JSON.stringify({status:step[0]})});notify('Đã cập nhật giao hàng mô phỏng');done()}catch(e){fail((e as Error).message)}}}>{step[1]}</button>}</>;
}
