export type MapLabelBox = {id:number;x:number;y:number;width:number;height:number;priority:number};
export type MapLabelPlacement = {id:number;x:number;y:number;visible:boolean};

/** Screen-space layout only; never changes geographic positions or voyage data. */
export function layoutMapLabels(labels:MapLabelBox[],width:number,height:number):MapLabelPlacement[] {
  const padding=12,gap=6;
  const placed:{left:number;top:number;right:number;bottom:number}[]=[];
  const offsets=[[0,0],[0,-32],[0,32],[-32,0],[32,0],[-32,-32],[32,32],[-32,32],[32,-32]];
  return [...labels].sort((a,b)=>b.priority-a.priority||a.id-b.id).map(label=>{
    const hidden={id:label.id,x:label.x,y:label.y,visible:false};
    if(![label.x,label.y,label.width,label.height,width,height].every(Number.isFinite)||label.width<=0||label.height<=0||label.width>width-2*padding||label.height>height-2*padding)return hidden;
    for(const [dx,dy] of offsets){
      const x=Math.max(padding+label.width/2,Math.min(width-padding-label.width/2,label.x+dx));
      const y=Math.max(padding+label.height/2,Math.min(height-padding-label.height/2,label.y+dy));
      const box={left:x-label.width/2,top:y-label.height/2,right:x+label.width/2,bottom:y+label.height/2};
      if(placed.some(other=>box.left<other.right+gap&&box.right>other.left-gap&&box.top<other.bottom+gap&&box.bottom>other.top-gap))continue;
      placed.push(box);
      return {id:label.id,x,y,visible:true};
    }
    return hidden;
  });
}
