import {useState,useEffect,useRef} from 'react';
import {api,Account,Cart,money} from '../api';
export function CartView({account,fail,checkout}:{account:Account|null;fail:(s:string)=>void;checkout:()=>void}){
 const [cart,setCart]=useState<Cart|null>(null);const revision=useRef(0);
 const load=()=>{const id=++revision.current;return api<Cart>('/cart').then(r=>{if(id===revision.current)setCart(r)}).catch(e=>fail(e.message))};
 useEffect(()=>{if(account)load();const changed=()=>{if(account)load()};window.addEventListener('cart-updated',changed);return()=>{revision.current++;window.removeEventListener('cart-updated',changed)}},[account]);
 if(!account)return <section className="empty"><h1>Giỏ hàng</h1><p>Vui lòng đăng nhập để xem giỏ hàng.</p></section>;
 async function change(id:number,quantity:number){try{setCart(await api('/cart/items',{method:'PUT',body:JSON.stringify({articleID:id,quantity})}))}catch(e){fail((e as Error).message)}}
 return <section className="panel"><p className="eyebrow">YOUR SELECTION</p><h1>Giỏ hàng của bạn</h1>{cart?.items.map(p=><div className="cart-row" key={p.articleID}><img src={'/api/products/'+p.articleID+'/image'} alt=""/><div><h3>{p.productName}</h3><strong>{money(p.price)}</strong></div><label>Số lượng<input type="number" min="1" max="99" value={p.quantity} onChange={e=>change(p.articleID,Number(e.target.value))}/></label><button onClick={async()=>{try{setCart(await api('/cart/items/'+p.articleID,{method:'DELETE'}))}catch(e){fail((e as Error).message)}}}>Xóa</button></div>)}{!cart?.items.length?<p>Giỏ hàng đang trống.</p>:<div className="section-top"><h2>Tổng: {money(cart.total)}</h2><button className="primary" onClick={checkout}>Tiến hành đặt hàng →</button></div>}</section>
}
