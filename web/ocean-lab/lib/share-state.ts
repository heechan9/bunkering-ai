// Share only public display selections; never credentials or arbitrary query parameters.
export type ShareState={policy:string;checkpoint:string;caseSeed:string;step:number;region:string;tab:string;view:string;lang:'ko'|'en';started:boolean};
const allowed={policy:['double_dqn','safe_stock','price_reactive','fixed_fueling'],checkpoint:['42','1042','2042','3042'],region:['hormuz','suez','cape','taiwan','bab','dover','ulsan'],tab:['geography','explore','compare'],view:['geography','route','ship','tank']};
export function readShareState(search:string):ShareState|null{
 const p=new URLSearchParams(search);if(p.get('share')!=='1')return null;
 const pick=(key:keyof typeof allowed)=>{const v=p.get(key);return v&&allowed[key].includes(v)?v:allowed[key][0]};
 const integer=(key:string,min:number,max:number,fallback:number)=>{const raw=p.get(key);if(!raw||!/^\d+$/.test(raw))return fallback;const n=Number(raw);return Number.isInteger(n)&&n>=min&&n<=max?n:fallback};
 return {policy:pick('policy'),checkpoint:pick('checkpoint'),caseSeed:String(integer('case',42,141,42)),step:integer('step',0,30,0),region:pick('region'),tab:pick('tab'),view:pick('view'),lang:p.get('lang')==='en'?'en':'ko',started:p.get('started')==='1'};
}
export function shareURL(origin:string,pathname:string,s:ShareState){
 const u=new URL(pathname,origin);u.search='';u.hash='';
 for(const [k,v]of Object.entries({share:'1',policy:s.policy,checkpoint:s.checkpoint,case:s.caseSeed,step:s.started?s.step:0,region:s.region,tab:s.tab,view:s.view,lang:s.lang,started:s.started?'1':'0'}))u.searchParams.set(k,String(v));
 return u.href;
}
