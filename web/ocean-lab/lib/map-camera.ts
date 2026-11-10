// Deterministic fit for an illustrative rectangular map, not a geographic transform.
export function mapCameraFit(viewWidth:number,viewHeight:number,mapWidth:number,mapDepth:number){
 const aspect=Math.max(.1,viewWidth/Math.max(1,viewHeight));
 const halfFov=19*Math.PI/180;
 const limitingAngle=Math.atan(Math.tan(halfFov)*Math.min(1,aspect));
 const radius=Math.hypot(mapWidth/2,mapDepth/2,12);
 const distance=radius/Math.sin(limitingAngle)*1.08;
 return {aspect,distance,minDistance:Math.max(18,Math.min(mapWidth,mapDepth)*.14),maxDistance:distance*2.5};
}

// Keep the center on the map footprint; camera and target move together.
export function mapCameraTarget(x:number,z:number,mapWidth:number,mapDepth:number){
 return {x:Math.max(-mapWidth/2,Math.min(mapWidth/2,x)),y:0,z:Math.max(-mapDepth/2,Math.min(mapDepth/2,z))};
}
