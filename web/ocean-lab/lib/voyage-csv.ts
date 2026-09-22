// Local-only CSV intake. One row per vessel/voyage/fuel; no inferred units or joins.
export const headers=['vessel_id','voyage_id','fuel_type','departure_at','arrival_at','unit','opening','supplied','consumed','closing','supply_basis','source_ref'];
export type Review={row:number;status:string;residual:number|null;issues:string[]};
export function parseCSV(text:string):string[][]{
 if(text.length>5*1024*1024)throw Error('CSV exceeds 5 MB');
 text=text.replace(/^\uFEFF/,'');if(text.includes('\0'))throw Error('Binary or UTF-16 input is not supported');
 const rows:string[][]=[];let row:string[]=[],cell='',quoted=false,closed=false;
 const push=()=>{row.push(cell);cell='';closed=false;if(row.length>100)throw Error('Too many columns')};
 const end=()=>{push();if(row.some(v=>v.trim()))rows.push(row);row=[];if(rows.length>10001)throw Error('Maximum 10,000 rows')};
 for(let i=0;i<text.length;i++){const c=text[i];if(quoted){if(c==='"'){if(text[i+1]==='"'){cell+='"';i++}else{quoted=false;closed=true}}else cell+=c}else if(c===',')push();else if(c==='\n'||c==='\r'){if(c==='\r'&&text[i+1]==='\n')i++;end()}else if(c==='"'){if(cell||closed)throw Error('Invalid CSV quotes');quoted=true}else{if(closed)throw Error('Unexpected text after quote');cell+=c}}
 if(quoted)throw Error('Unclosed CSV quote');if(cell||row.length||closed)end();if(!rows.length)throw Error('Empty CSV');
 if(rows[0].some(h=>!h.trim())||new Set(rows[0]).size!==rows[0].length)throw Error('Empty or duplicate header');
 if(rows.some(r=>r.length!==rows[0].length))throw Error('Inconsistent column count');return rows;
}
export function exportCSV(rows:unknown[][]){return '\uFEFF'+rows.map(row=>row.map(v=>{let s=String(v??'');if(/^[\s]*[=+\-@]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"'}).join(',')).join('\r\n')}
export function reviewVoyages(rows:string[][],tolerance:number):Review[]{
 if(!Number.isFinite(tolerance)||tolerance<0)throw Error('Invalid tolerance');
 const h=rows[0];if(!h||headers.some(k=>!h.includes(k))||h.length!==headers.length)throw Error('Use the template headers');
 if(rows.length<2)throw Error('No voyage rows');
 const records=rows.slice(1).map(r=>Object.fromEntries(h.map((k,i)=>[k,r[i].trim()])));
 const key=(r:Record<string,string>)=>JSON.stringify([r.vessel_id,r.voyage_id,r.fuel_type]);
 const counts=new Map<string,number>();for(const r of records)counts.set(key(r),(counts.get(key(r))??0)+1);
 return records.map((r,i)=>{const issues:string[]=[];
 for(const k of ['vessel_id','voyage_id','fuel_type','source_ref'])if(!r[k])issues.push('missing:'+k);
 if((counts.get(key(r))??0)>1)issues.push('duplicate-voyage-fuel');
 if(!['t','kg','m3','L'].includes(r.unit))issues.push('unconfirmed-unit');
 if(r.supply_basis!=='actual')issues.push('supply-not-confirmed-actual');
 const iso=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/;
 for(const k of ['departure_at','arrival_at'])if(!iso.test(r[k])||!Number.isFinite(Date.parse(r[k]))||new Date(r[k].slice(0,10)+'T00:00:00Z').toISOString().slice(0,10)!==r[k].slice(0,10))issues.push('invalid-time:'+k);
 if(!issues.some(v=>v.startsWith('invalid-time'))&&Date.parse(r.arrival_at)<=Date.parse(r.departure_at))issues.push('time-order');
 const n=['opening','supplied','consumed','closing'].map(k=>{const v=r[k];if(!/^(?:\d+)(?:\.\d+)?$/.test(v)||!Number.isFinite(Number(v))){issues.push('invalid-number:'+k);return NaN}return Number(v)});
 if(issues.length)return {row:i+2,status:'held',residual:null,issues};
 const residual=n[0]+n[1]-n[2]-n[3];if(!Number.isFinite(residual))return {row:i+2,status:'held',residual:null,issues:['numeric-overflow']};
 return {row:i+2,status:Math.abs(residual)<=tolerance?'balanced':'review',residual,issues:Math.abs(residual)<=tolerance?[]:['balance-outside-tolerance']};
 });
}
export async function readCSVFile(file:File,encoding:string){if(file.size>5*1024*1024)throw Error('CSV exceeds 5 MB');const bytes=await file.arrayBuffer();return parseCSV(new TextDecoder(encoding,{fatal:true}).decode(bytes))}
export async function fileDigest(file:File){if(!globalThis.crypto?.subtle)throw Error('CSV review requires a secure HTTPS connection for SHA-256. Open the published HTTPS site.');const bytes=await file.arrayBuffer();const hash=await crypto.subtle.digest('SHA-256',bytes);return Array.from(new Uint8Array(hash),v=>v.toString(16).padStart(2,'0')).join('')}

// Counts describe declared fields, not authenticity or operational safety.
export function summarizeColumns(rows:string[][],reviews:Review[]){
 return (rows[0]??[]).map((field,index)=>{
  let missing=0,invalid=0;
  for(let i=1;i<rows.length;i++){
   const value=(rows[i][index]??'').trim();
   if(!value){missing++;continue}
   const issues=reviews[i-1]?.issues??[];
   if(issues.includes('invalid-number:'+field)||issues.includes('invalid-time:'+field)||
    (field==='unit'&&issues.includes('unconfirmed-unit'))||
    (field==='supply_basis'&&issues.includes('supply-not-confirmed-actual')))invalid++;
  }
  return {field,total:rows.length-1,missing,invalid};
 });
}
