'use client';
import {useLocale} from '@/lib/locale';
import catalog from '@/public/data/source-catalog.json';

export default function SourceInventory(){
 const {lang}=useLocale(); const en=lang==='en'; const locale=en?'en':'ko';
 return <details className="voyage-review source-catalog"><summary>{en?'Sources and confirmation status':'자료 출처·확인 상태'}</summary>
  <p>{en?`Source descriptions reviewed on ${catalog.reviewed_on}. Record periods are listed separately. Links preserve the reviewed version.`:`자료 설명 검토일: ${catalog.reviewed_on}. 실제 자료 기간은 아래에 따로 표시하며, 근거 링크는 검토한 버전으로 고정됩니다.`}</p>
  <p>{en?'Source verification and model performance are separate. Locally uploaded files are reviewed in the voyage CSV section.':'자료 확인과 모델 성능 검증은 구분합니다. 직접 올린 파일은 항차 CSV 검토에서 별도로 확인합니다.'}</p>
  <a href="/data/source-catalog.json" download="bunkering-source-catalog.json">{en?'Download source catalog (JSON)':'자료 목록 내려받기 (JSON)'}</a>
  <div className="source-catalog-grid">{catalog.sources.map(s=><article className="source-catalog-card" key={s.id}>
   <h3>{s.title[locale]}</h3><p className="source-kind">{s.kind[locale]}</p>
   <dl>{(['unit','period','scope','status','limits'] as const).map((field,i)=><div key={field}><dt>{(en?['Units','Record period','Coverage','Checked','Still needed']:['단위','자료 기간','집계 범위','확인한 내용','남은 확인사항'])[i]}</dt><dd>{s[field][locale]}</dd></div>)}</dl>
   <a href={s.url} target="_blank" rel="noreferrer">{en?'Open reviewed evidence':'검토한 근거 보기'}</a>
   <details><summary>{en?'Record identification':'근거 파일 식별 정보'}</summary><p className="file-hash">{s.path}</p><p className="file-hash">SHA-256: {s.sha256}</p><p>{s.bytes.toLocaleString(locale)} bytes · {catalog.revision.slice(0,7)}</p><p>{en?'Identifies the public supporting document, not the private original or proof of authenticity.':'공개 근거 문서를 식별하는 값입니다. 비공개 원본의 해시나 진위 인증이 아닙니다.'}</p></details>
  </article>)}</div>
 </details>;
}
