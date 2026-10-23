/** Visible before the disabled replay-start controls, not behind `started`. */
export default function ReplayLoadNotice({ready,failed,retry,t}:{
  ready:boolean;failed:boolean;retry:()=>void;t:(text:string)=>string;
}) {
  if(ready)return null;
  if(failed)return <div role="alert" className="share-fallback">
    <p>{t('항차 기록을 불러오지 못했어요. 다시 시도해 주세요.')}</p>
    <button type="button" onClick={retry}>{t('항차 기록 다시 불러오기')}</button>
  </div>;
  return <p role="status" className="small-muted">{t('원본 항차 기록을 불러오는 중…')}</p>;
}
