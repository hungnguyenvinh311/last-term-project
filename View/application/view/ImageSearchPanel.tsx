import React from 'react';

export type DetectedRegion={label:string;categoryID?:number|null;score:number;region:number[]};
const labels=['Tất cả','Điện thoại','Laptop','Máy tính bảng','Tai nghe','Đồng hồ'];

export function regionCategory(region:DetectedRegion|null):number{
 if(!region)return 0;
 if(region.categoryID&&region.categoryID>=1&&region.categoryID<=5)return region.categoryID;
 // Compatibility with detector responses created before categoryID was introduced.
 const known:Record<string,number>={'a mobile phone':1,smartphone:1,'a laptop computer':2,'a tablet computer':3,headphones:4,'a smartwatch':5};
 return known[region.label.toLowerCase()]||0;
}

type Props={preview:string;filename:string;regions:DetectedRegion[];region:number[]|null;imageCategory:number;busy:boolean;
 onSelect:(region:DetectedRegion|null)=>void;onCategory:(category:number)=>void;onDetect:()=>void;onRemove:()=>void};

export function ImageSearchPanel(p:Props){
 const selected=(r:DetectedRegion)=>JSON.stringify(r.region)===JSON.stringify(p.region);
 return <div className="image-analysis">
  <div className="detection-preview"><img src={p.preview} alt="Ảnh tìm kiếm"/>
   {p.regions.map((r,i)=><div key={i} className={'detection-box'+(selected(r)?' chosen':'')}
    style={{left:`${r.region[0]*100}%`,top:`${r.region[1]*100}%`,width:`${(r.region[2]-r.region[0])*100}%`,height:`${(r.region[3]-r.region[1])*100}%`}}>
    <button type="button" className="detection-label" aria-label={'Select region '+(i+1)} onClick={()=>p.onSelect(r)}>{i+1}. {r.label} {r.score.toFixed(2)}</button></div>)}
  </div>
  <div><p>{p.filename}</p><button onClick={p.onDetect} disabled={p.busy}>Nhận diện sản phẩm trong ảnh</button>
   {p.regions.length>0&&<p className="muted">Bấm nhãn trên khung hoặc chọn vùng bên dưới.</p>}
   <label>Vùng tìm kiếm<select aria-label="Vùng tìm kiếm" value={p.region?JSON.stringify(p.region):''}
    onChange={e=>p.onSelect(p.regions.find(r=>JSON.stringify(r.region)===e.target.value)||null)}>
    <option value="">Dùng toàn ảnh</option>{p.regions.map((r,i)=><option key={i} value={JSON.stringify(r.region)}>{i+1}. {r.label}</option>)}
   </select></label>
   <label>Loại sản phẩm trong ảnh<select aria-label="Loại sản phẩm trong ảnh" value={p.imageCategory} onChange={e=>p.onCategory(Number(e.target.value))}>
    <option value={0}>{p.region?'Chưa xác định — hãy chọn loại':'Tự động từ toàn ảnh'}</option>
    {labels.slice(1).map((label,i)=><option key={i+1} value={i+1}>{label}</option>)}
   </select></label>
   {p.imageCategory>0&&<p className="muted" role="status">Chỉ tìm trong nhóm: {labels[p.imageCategory]}. Bạn có thể sửa loại nếu nhận diện sai.</p>}
   {p.regions.length>1&&!p.region&&<p className="muted">Ảnh có nhiều vùng sản phẩm. Hãy chọn khung muốn tìm; hiện đang dùng toàn ảnh.</p>}
   {p.region&&!p.imageCategory&&<p role="status">Hãy chọn loại sản phẩm cho vùng ảnh trước khi tìm kiếm.</p>}
   <button onClick={p.onRemove}>Bỏ ảnh</button>
  </div>
 </div>;
}
