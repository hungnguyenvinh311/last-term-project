const labels:Record<string,string>={black:'Đen',white:'Trắng',red:'Đỏ',blue:'Xanh dương',green:'Xanh lá',yellow:'Vàng',pink:'Hồng',purple:'Tím',silver:'Bạc',gray:'Xám',orange:'Cam',brown:'Nâu'};
export function photoColour(specs:Record<string,unknown>|null){
 const raw=specs?.['Màu ảnh đại diện'];
 const value=typeof raw==='string'?raw:'';
 return value?(labels[value]||value):null;
}
