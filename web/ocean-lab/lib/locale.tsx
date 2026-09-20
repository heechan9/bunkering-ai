'use client';
import {createContext,useCallback,useContext,useEffect,useSyncExternalStore} from 'react';
import en from './en.json';
type Lang='ko'|'en';
export function translate(lang:Lang,text:string,...values:unknown[]){
 const key=text.trim();const translated=lang==='en'?(en as Record<string,string>)[key]:undefined;
 const value=translated===undefined?text:text.slice(0,text.indexOf(key))+translated+text.slice(text.indexOf(key)+key.length);
 return value.replace(/\{(\d+)\}/g,(_,i)=>String(values[Number(i)]??''));
}
const Context=createContext<{lang:Lang;setLang:(lang:Lang)=>void;t:(text:string,...values:unknown[])=>string}>({lang:'ko',setLang:()=>{},t:(text:string,...values:unknown[])=>translate('ko',text,...values)});
let memoryLanguage:Lang='ko';
function languageSnapshot():Lang {try{const saved=localStorage.getItem('ocean-lab-language');if(saved==='en'||saved==='ko')return saved}catch{}return memoryLanguage}
const serverLanguage=():Lang=>'ko';
function subscribeLanguage(notify:()=>void){window.addEventListener('storage',notify);window.addEventListener('ocean-lab-language-change',notify);return()=>{window.removeEventListener('storage',notify);window.removeEventListener('ocean-lab-language-change',notify)}}
export function LocaleProvider({children}:{children:React.ReactNode}){
 const lang=useSyncExternalStore(subscribeLanguage,languageSnapshot,serverLanguage);
 useEffect(()=>{document.documentElement.lang=lang},[lang]);
 const change=useCallback((next:Lang)=>{memoryLanguage=next;try{localStorage.setItem('ocean-lab-language',next)}catch{}window.dispatchEvent(new Event('ocean-lab-language-change'))},[]);
 const t=useCallback((text:string,...values:unknown[])=>translate(lang,text,...values),[lang]);
 return <Context.Provider value={{lang,setLang:change,t}}>{children}</Context.Provider>;
}
export const useLocale=()=>useContext(Context);
