/** Presentation-only clock: one loop takes 48 seconds of visible playback. */
export function advancePassageProgress(progress:number,elapsedMs:number,speed:number):number {
 if(!Number.isFinite(elapsedMs)||elapsedMs<=0||!Number.isFinite(speed)||speed<=0)return progress;
 return (progress+elapsedMs/48000*speed)%1;
}
