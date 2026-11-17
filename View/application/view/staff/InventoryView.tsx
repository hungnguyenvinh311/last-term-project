import {useEffect,useState} from 'react';
import {api,post} from '../../api';
import type {Feedback} from '../StaffView';

type StockRow={articleID:number;productName:string;brand:string;groupName:string;subCategory:string;onHandQuantity:number;committedQuantity:number;availableQuantity:number};

export function InventoryView({fail,notify}:Feedback){
 const [rows,setRows]=useState<StockRow[]>([]),[busy,setBusy]=useState(false),[adjustID,setAdjustID]=useState<number|null>(null);
 const load=()=>api<StockRow[]>('/staff/inventory').then(setRows).catch(e=>fail(e.message));
 useEffect(()=>{load()},[]);
 async function receive(e:React.FormEvent<HTMLFormElement>){e.preventDefault();const form=e.currentTarget;const data=Object.fromEntries(new FormData(form));setBusy(true);try{await api('/staff/inventory/receipts',post({receiptNumber:data.receiptNumber,items:[{articleID:Number(data.articleID),quantity:Number(data.quantity)}]}));form.reset();notify('Đã ghi nhận phiếu nhập kho');await load()}catch(e){fail((e as Error).message)}finally{setBusy(false)}}
 async function adjust(e:React.FormEvent<HTMLFormElement>,articleID:number){e.preventDefault();const form=e.currentTarget;const data=Object.fromEntries(new FormData(form));setBusy(true);try{await api(`/staff/inventory/${articleID}/adjustments`,post({delta:Number(data.delta),reason:data.reason}));setAdjustID(null);notify('Đã điều chỉnh tồn kho và ghi nhật ký');await load()}catch(e){fail((e as Error).message)}finally{setBusy(false)}}
 return <><h2>Kho và tồn khả dụng</h2><p className="muted">Tồn khả dụng = tồn vật lý − hàng đang giữ hoặc đã phân bổ. Phiếu nhập được ghi một lần theo mã phiếu.</p>
 <form className="inventory-receipt" onSubmit={receive}><h3>Ghi nhận nhập kho</h3><label>Mã phiếu<input name="receiptNumber" minLength={3} maxLength={255} required/></label><label>Sản phẩm<select name="articleID" required defaultValue="">{<option value="" disabled>Chọn sản phẩm</option>}{rows.map(r=><option key={r.articleID} value={r.articleID}>#{r.articleID} · {r.productName}</option>)}</select></label><label>Số lượng nhận<input name="quantity" type="number" min="1" max="100000" required/></label><button className="primary" disabled={busy}>Ghi phiếu nhập</button></form>
 <div className="table-scroll"><table><thead><tr><th>Mã / sản phẩm</th><th>Danh mục</th><th>Thương hiệu</th><th>Tồn vật lý</th><th>Đang giữ / phân bổ</th><th>Tồn khả dụng</th><th>Điều chỉnh</th></tr></thead><tbody>{rows.map(r=><tr key={r.articleID}><td>#{r.articleID} · {r.productName}</td><td>{r.groupName} · {r.subCategory}</td><td>{r.brand}</td><td>{r.onHandQuantity}</td><td>{r.committedQuantity}</td><td><b>{r.availableQuantity}</b></td><td>{adjustID===r.articleID?<form onSubmit={e=>adjust(e,r.articleID)}><label>Thay đổi (+/−)<input name="delta" type="number" required min="-100000" max="100000" defaultValue="0"/></label><label>Lý do<input name="reason" minLength={3} maxLength={255} required/></label><button disabled={busy}>Lưu</button><button type="button" onClick={()=>setAdjustID(null)}>Hủy</button></form>:<button onClick={()=>setAdjustID(r.articleID)}>Điều chỉnh</button>}</td></tr>)}</tbody></table></div></>;
}
