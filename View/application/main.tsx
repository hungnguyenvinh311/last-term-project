import React,{useState,useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {api,post,Account} from './api';
import {MainView} from './view/MainView';
import {CartView} from './view/CartView';
import {CheckoutView} from './view/CheckoutView';
import {StaffView,type EmployeeRole} from './view/StaffView';
import {ProfileView} from './view/ProfileView';
import './styles.css';

function App(){
 const [page,setPage]=useState('shop'),[account,setAccount]=useState<Account|null>(null),[error,setError]=useState(''),[notice,setNotice]=useState(''),[form,setForm]=useState(false),[register,setRegister]=useState(false),[profile,setProfile]=useState<any>(null);
 useEffect(()=>{if(sessionStorage.getItem('token'))api('/accounts/me').then(r=>{setAccount(r.account);setProfile(r.profile)}).catch(e=>setError(e.message));},[]);
 const notify=(message:string)=>{setNotice(message);setError('')};
 async function auth(e:React.FormEvent<HTMLFormElement>){e.preventDefault();setError('');const d=Object.fromEntries(new FormData(e.currentTarget));try{if(register){await api('/accounts/register',post(d));setRegister(false);notify('Đăng ký thành công. Hãy đăng nhập.');return}const r=await api('/accounts/login',post(d));sessionStorage.setItem('token',r.token);setAccount(r.account);setForm(false);setProfile((await api('/accounts/me')).profile);notify('Đã đăng nhập')}catch(e){setError((e as Error).message)}}
 async function logout(){try{await api('/accounts/logout',post({}))}catch{}sessionStorage.removeItem('token');setAccount(null);setProfile(null);setPage('shop')}
 return <><header><a className="logo" href="#" onClick={()=>setPage('shop')}>electra<span>AI ELECTRONICS</span></a><nav><button onClick={()=>setPage('shop')}>Khám phá</button>{account?.role==='customer'&&<><button onClick={()=>setPage('cart')}>Giỏ hàng</button><button onClick={()=>setPage('orders')}>Đơn hàng</button></>}{account&&account.role!=='customer'&&<button onClick={()=>setPage('staff')}>Quản trị · {account.role}</button>}</nav><div>{account?<>{account.role==='customer'&&<button onClick={()=>setPage('profile')}>{account.email}</button>}<button onClick={logout}>Đăng xuất</button></>:<button className="primary" onClick={()=>setForm(true)}>Đăng nhập</button>}</div></header>
 <div className="demo">COURSEWORK DEMO · Thanh toán và vận chuyển mô phỏng · Giá là dữ liệu tại thời điểm thu thập</div>
 <main>{error&&<div role="alert" className="alert error">{error}<button onClick={()=>setError('')}>×</button></div>}{notice&&<div role="status" className="alert">{notice}<button onClick={()=>setNotice('')}>×</button></div>}
 {page==='shop'&&<MainView account={account} notify={notify} fail={setError}/>}
 {page==='cart'&&<CartView account={account} fail={setError} checkout={()=>setPage('checkout')}/>}
 {(page==='checkout'||page==='orders')&&<CheckoutView account={account} mode={page} fail={setError} notify={notify} finished={()=>setPage('orders')}/>}
 {page==='staff'&&account&&account.role!=='customer'&&<StaffView role={account.role as EmployeeRole} fail={setError} notify={notify}/>}
 {page==='profile'&&profile&&<ProfileView fail={setError} notify={notify} onSave={setProfile}/>}
 </main><footer className="site-footer"><div className="footer-copy"><b>Electra · cửa hàng minh họa</b><p>Hỗ trợ: support@electra-demo.local</p><p>Hotline minh họa: 1900 0000</p><p>Vị trí bản đồ: Hà Nội, Việt Nam</p><a href="https://www.google.com/maps/search/?api=1&query=Hanoi%2C%20Vietnam" target="_blank" rel="noreferrer">Mở bản đồ Hà Nội</a><small>Thông tin liên hệ và địa điểm chỉ dùng cho bản demo môn học.</small></div><iframe title="Bản đồ Hà Nội" src="https://maps.google.com/maps?q=Hanoi%2C%20Vietnam&output=embed" loading="lazy" referrerPolicy="no-referrer-when-downgrade"/></footer>
 {form&&<div className="overlay"><section className="dialog"><button className="close" onClick={()=>setForm(false)}>×</button><p className="eyebrow">YOUR ELECTRA ACCOUNT</p><h2>{register?'Tạo tài khoản':'Chào mừng trở lại'}</h2><form onSubmit={auth}>{register&&<label>Họ tên<input name="fullName" required maxLength={150}/></label>}<label>Email<input name="email" type="email" required autoComplete="username"/></label><label>Mật khẩu<input name="password" type="password" required minLength={register?10:1} maxLength={128} autoComplete={register?'new-password':'current-password'}/></label><button className="primary">{register?'Đăng ký':'Đăng nhập'}</button></form><button onClick={()=>setRegister(!register)}>{register?'Đã có tài khoản? Đăng nhập':'Chưa có tài khoản? Đăng ký'}</button></section></div>}
 </>;
}
createRoot(document.getElementById('root')!).render(<App/>);
