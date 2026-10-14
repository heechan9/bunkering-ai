'use client';
import {useEffect} from 'react';
import Link from 'next/link';

const target='/?share=1&region=arctic&tab=explore&view=geography';
export default function ArcticPage(){
 useEffect(()=>{const language=new URLSearchParams(window.location.search).get('lang');window.location.replace(target+(language==='en'?'&lang=en':''))},[]);
 return <main className="arctic-page"><p role="status">북극항로 운항 체험으로 이동합니다. / Opening the Arctic map voyage.</p><Link href={target}>북극 지도 운항 체험 열기 / Open Arctic map voyage</Link></main>;
}
