import {useEffect,useState} from 'react';
import {api} from '../api';
import {todayInVietnam} from '../businessDate';
export function ProfileView({fail,notify,onSave}:{fail:(s:string)=>void;notify:(s:string)=>void;onSave:(p:any)=>void}){
 const [profile,setProfile]=useState<any>(null);
 useEffect(()=>{api('/accounts/me').then(r=>setProfile(r.profile)).catch(e=>fail(e.message))},[]);
 if(!profile)return <p>Đang tải hồ sơ…</p>;
 return <section className="panel"><h1>Hồ sơ của bạn</h1><form onSubmit={async e=>{e.preventDefault();try{const d=Object.fromEntries(new FormData(e.currentTarget));const p=await api('/accounts/me',{method:'PUT',body:JSON.stringify({...d,dateOfBirth:d.dateOfBirth||null})});setProfile(p);onSave(p);notify('Đã cập nhật hồ sơ')}catch(e){fail((e as Error).message)}}}><label>Họ tên<input name="fullName" required maxLength={150} defaultValue={profile.fullName}/></label><label>Ngày sinh<input name="dateOfBirth" type="date" min="1900-01-01" max={todayInVietnam()} defaultValue={profile.dateOfBirth||''}/></label><label>Số điện thoại<input name="phoneNumber" maxLength={30} defaultValue={profile.phoneNumber||''}/></label><p className="muted">??a ch? nh?n h?ng ???c nh?p ri?ng cho t?ng ??n h?ng.</p><button className="primary">Lưu hồ sơ</button></form></section>;
}
