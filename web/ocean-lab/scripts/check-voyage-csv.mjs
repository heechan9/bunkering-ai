import assert from 'node:assert/strict';
import {headers,parseCSV,exportCSV,reviewVoyages,readCSVFile} from '../lib/voyage-csv.ts';
const row=['ship1','voyage1','VLSFO','2026-09-01T00:00:00+09:00','2026-09-02T00:00:00+09:00','t','100','20','30','90','actual','log-page-1'];
const review=r=>reviewVoyages([headers,r],0.01)[0];
assert.equal(review(row).status,'balanced');
for(const [field,value]of [['opening',''],['unit','unknown'],['supply_basis','planned'],['departure_at','2026-02-30T00:00:00Z'],['arrival_at','2026-08-01T00:00:00Z'],['consumed','NaN']]){const bad=[...row];bad[headers.indexOf(field)]=value;assert.equal(review(bad).status,'held',field)}
const zero=[...row];zero[7]='0';zero[9]='70';assert.equal(review(zero).status,'balanced');
assert(reviewVoyages([headers,row,row],0).every(r=>r.status==='held'));
const mismatch=[...row];mismatch[9]='80';assert.equal(review(mismatch).status,'review');
assert.deepEqual(parseCSV(exportCSV([headers,row])),[headers,row]);
assert(exportCSV([['=SUM(A1)','@test']]).includes("'=SUM"));
assert.throws(()=>parseCSV('a,a\n1,2'));assert.throws(()=>parseCSV('a,b\n1'));assert.throws(()=>parseCSV('a\n"unfinished'));
const cp949=new File([new Uint8Array([0x61,0x0a,0xb0,0xa1])],'k.csv');assert.equal((await readCSVFile(cp949,'euc-kr'))[1][0],'가');
console.log('PASS: CSV, zero/missing, dates, duplicates, units, supply basis, balances, safe export and CP949');
