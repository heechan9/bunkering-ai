'use client';
import {createContext,useCallback,useContext,useEffect,useState} from 'react';
import en from './en.json';
type Lang='ko'|'en';
export function translate(lang:Lang,text:string,...values:unknown[]){
 const key=text.trim();const translated=lang==='en'?(en as Record<string,string>)[key]:undefined;
 const value=translated===undefined?text:text.slice(0,text.indexOf(key))+translated+text.slice(text.indexOf(key)+key.length);
 return value.replace(/\{(\d+)\}/g,(_,i)=>String(values[Number(i)]??''));
}
const Context=createContext({lang:'ko' as Lang,setLang:(_lang:Lang)=>{},t:(text:string,...values:unknown[])=>translate('ko',text,...values)});
export function LocaleProvider({children}:{children:React.ReactNode}){
 const [lang,setLang]=useState<Lang>('ko');
 useEffect(()=>{try{const saved=localStorage.getItem('ocean-lab-language');if(saved==='en'||saved==='ko')setLang(saved)}catch{}},[]);
 useEffect(()=>{document.documentElement.lang=lang},[lang]);
 const change=useCallback((next:Lang)=>{setLang(next);try{localStorage.setItem('ocean-lab-language',next)}catch{}},[]);
 const t=useCallback((text:string,...values:unknown[])=>translate(lang,text,...values),[lang]);
 return <Context.Provider value={{lang,setLang:change,t}}>{children}</Context.Provider>;
}
export const useLocale=()=>useContext(Context);
