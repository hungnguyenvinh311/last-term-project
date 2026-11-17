export type Product={articleID:number;categoryID:number;productName:string;brand:string|null;price:number;currency:string;imageUrl:string|null;technicalSpecs:Record<string,string|number|boolean|null>|null;description?:string;warrantyTerms?:string;availableQuantity:number;onHandQuantity:number;fallback?:boolean;score?:number;matchDetails?:{metric:string;embedding:number|null;text:number|null;keyword:number;rankScore:number;mode:string}};
export type Account={accountID:number;customerID:number|null;employeeID:number|null;userID:number;email:string;role:'customer'|'Admin'|'Sales Staff'|'Warehouse Staff'|'Manager';isActive:boolean};
export type Cart={items:Array<{articleID:number;productName:string;quantity:number;price:number;currency:string;isActive:boolean}>;total:number;pricing?:{itemSubTotal:number;shippingFee:number;discountAmount:number;totalAmount:number}};
export const money=(n:number)=>new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND'}).format(Number(n));
let context=sessionStorage.getItem('searchContext') || crypto.randomUUID();sessionStorage.setItem('searchContext',context);
export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
  const headers=new Headers(options.headers); const token=sessionStorage.getItem('token');
  if(token)headers.set('Authorization','Bearer '+token);
  headers.set('X-Search-Context',context);
  if(options.body && !(options.body instanceof FormData))headers.set('Content-Type','application/json');
  const response=await fetch('/api'+path,{...options,headers});
  const data=await response.json();
  if(!response.ok){if(response.status===401)sessionStorage.removeItem('token');throw new Error(typeof data.detail==='string'?data.detail:'Yêu cầu không hợp lệ');}
  return data;
}
export const post=(body:unknown)=>({method:'POST',body:JSON.stringify(body)});
