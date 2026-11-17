// Match Orders.createdAt and reporting's Vietnam business day, including after midnight.
export const todayInVietnam=()=>new Intl.DateTimeFormat('sv-SE',{
 timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit'
}).format(new Date());
