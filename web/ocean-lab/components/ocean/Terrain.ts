import * as THREE from 'three';
import type {TerrainData, Region} from '@/lib/ocean-types';

// DEM is a geographic display layer only; no simulation state enters here.
export function terrainHeight(data:TerrainData, lon:number, lat:number) {
 const [w,s,e,n]=data.bounds;
 const x=Math.max(0,Math.min(data.width-1,Math.round((lon-w)/(e-w)*(data.width-1))));
 const y=Math.max(0,Math.min(data.height-1,Math.round((n-lat)/(n-s)*(data.height-1))));
 const k=y*data.width+x;
 return data.land[k]?Math.max(0,data.elevations[k]):0;
}

export function makeTerrain(data:TerrainData, cfg:Region, scale:number, exaggeration:number, software:boolean) {
 const stride=software?2:1, positions:number[]=[], colors:number[]=[], indices:number[]=[];
 const [w,s,e,n]=data.bounds, cosine=Math.cos(cfg.center[1]*Math.PI/180);
 const count=(data.width-1)/stride+1, mask:boolean[]=[];
 const low=new THREE.Color('#83927b'), middle=new THREE.Color('#b5aa89'), high=new THREE.Color('#d4d0c2');
 for(let row=0;row<data.height;row+=stride)for(let col=0;col<data.width;col+=stride){
  const k=row*data.width+col, metres=Math.max(0,data.elevations[k]), isLand=Boolean(data.land[k]);
  const lon=w+(e-w)*col/(data.width-1),lat=n-(n-s)*row/(data.height-1);
  positions.push((lon-cfg.center[0])*cosine*scale,isLand?.07+metres*scale/111320*exaggeration:.07,-(lat-cfg.center[1])*scale);
  const color=metres<1200?low.clone().lerp(middle,metres/1200):middle.clone().lerp(high,Math.min(1,(metres-1200)/2400));
  colors.push(color.r,color.g,color.b);mask.push(isLand);
 }
 for(let r=0;r<count-1;r++)for(let c=0;c<count-1;c++){
  const a=r*count+c,b=a+1,d=a+count,e=d+1;
  if(mask[a]&&mask[b]&&mask[d])indices.push(a,d,b);
  if(mask[b]&&mask[d]&&mask[e])indices.push(b,d,e);
 }
 const geometry=new THREE.BufferGeometry();
 geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));
 geometry.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));
 geometry.setIndex(indices);geometry.computeVertexNormals();
 const material=new THREE.MeshLambertMaterial({vertexColors:true,side:THREE.DoubleSide,flatShading:true});
 const mesh=new THREE.Mesh(geometry,material);mesh.renderOrder=100;
 return mesh;
}
