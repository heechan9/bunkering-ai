/** EPSG:3411 forward polar stereographic (Hughes 1980), display only. */
export function polarPoint(latitude:number,longitude:number):[number,number] {
  const rad=Math.PI/180,a=6378273,b=6356889.449,e=Math.sqrt(1-(b/a)**2);
  const t=(phi:number)=>Math.tan(Math.PI/4-phi/2)/((1-e*Math.sin(phi))/(1+e*Math.sin(phi)))**(e/2);
  const phi=70*rad,m=Math.cos(phi)/Math.sqrt(1-e*e*Math.sin(phi)**2),rho=a*m*t(latitude*rad)/t(phi);
  return gridPoint(rho*Math.sin((longitude+45)*rad),-rho*Math.cos((longitude+45)*rad));
}
export function gridPoint(x:number,y:number):[number,number] {return [320+x*.00007,320-y*.00007];}
export type TrackPoint=[string,number,number,number|null,number|null];
export type ObservedTrack={status:'available';id:string;citation:string;url:string;license:string;licenseUrl:string;rowCount:number;start:string;end:string;sourceSha256:string;fuelData:false;commercialNsrTransit:false;points:TrackPoint[]};
export type IceSnapshot={status:'available'|'unavailable';date:string;url:string;license:string;citation:string;sampleSpacingKm:number;nativeResolutionKm:number;cells:[number,number,number][];reason?:string};
export function validTrack(value:unknown):value is ObservedTrack {
  if(!value||typeof value!=='object')return false;
  const v=value as ObservedTrack;
  return v.status==='available'&&typeof v.start==='string'&&typeof v.end==='string'&&typeof v.citation==='string'&&typeof v.url==='string'&&v.url.startsWith('https://doi.org/')&&typeof v.licenseUrl==='string'&&v.licenseUrl.startsWith('https://creativecommons.org/')&&v.fuelData===false&&v.commercialNsrTransit===false&&Array.isArray(v.points)&&v.points.length>1&&v.rowCount===v.points.length&&v.points.every((p,i)=>Array.isArray(p)&&p.length===5&&(p[3]===null||(Number.isFinite(p[3])&&p[3]>=0))&&(p[4]===null||(Number.isFinite(p[4])&&p[4]>=0&&p[4]<=360))&&typeof p[0]==='string'&&Number.isFinite(p[1])&&Math.abs(p[1])<=90&&Number.isFinite(p[2])&&Math.abs(p[2])<=180&&(i===0||p[0]>v.points[i-1][0]));
}
export function validIce(value:unknown):value is IceSnapshot {
  if(!value||typeof value!=='object')return false;
  const v=value as IceSnapshot;
  return v.status==='available'&&/^\d{4}-\d{2}-\d{2}/.test(v.date)&&Number.isFinite(v.nativeResolutionKm)&&v.nativeResolutionKm>0&&Number.isFinite(v.sampleSpacingKm)&&v.sampleSpacingKm>0&&Array.isArray(v.cells)&&v.cells.length>0&&v.cells.every(p=>Array.isArray(p)&&p.length===3&&p.every(Number.isFinite)&&p[2]>=0&&p[2]<=1);
}
