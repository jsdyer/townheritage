export const STORAGE_KEY = 'coolcode:townheritage:saved:v1';
export function safeURL(value) {
  if (typeof value !== 'string' || value.length > 4000 || /\s/.test(value)) return '';
  try { const u = new URL(value); return u.protocol === 'https:' && !u.username && !u.password && ![...u.searchParams.keys()].some(k => /^(wskey|apikey|api_key|access_token|token|key)$/i.test(k)) ? u.href : ''; } catch { return ''; }
}
export const list = value => Array.isArray(value) ? value.filter(x => typeof x === 'string') : [];
export function record(value) {
  if (!value || typeof value.id !== 'string' || !value.id.startsWith('/') || typeof value.title !== 'string') return null;
  const r = { id: value.id, title: value.title, type: typeof value.type === 'string' ? value.type : 'IMAGE', rights: Array.isArray(value.rights) ? value.rights.filter(x => x && typeof x.label === 'string' && safeURL(x.url)).map(x => ({label:x.label,url:safeURL(x.url)})) : [], years: Array.isArray(value.years) ? value.years.filter(y => Number.isInteger(y) && y >= 1 && y <= 2100) : [] };
  for (const field of ['creators','description','institutions','aggregators','providerCountries','places','dateText','collections']) r[field] = list(value[field]);
  for (const field of ['thumbnail','original','source','europeana']) r[field] = safeURL(value[field]);
  r.capturedAt = typeof value.capturedAt === 'string' ? value.capturedAt : '';
  return r;
}
export function parseSaved(text) {
  try { const values = JSON.parse(text); return Array.isArray(values) ? [...new Map(values.slice(0,200).map(record).filter(Boolean).map(r => [r.id,r])).values()] : []; } catch { return []; }
}
export function filterRecords(records, state = {}) {
  const query = (state.query || '').trim().toLocaleLowerCase();
  let result = records.filter(r => (!state.collection || r.collections.includes(state.collection)) && (!state.institution || r.institutions.includes(state.institution)) && (!state.rights || r.rights.some(x => x.label === state.rights)) && (!state.decade || r.years.some(y => Math.floor(y/10)*10 === Number(state.decade))) && (!query || [r.title,...r.description,...r.creators,...r.places,...r.institutions,...r.dateText].join(' ').toLocaleLowerCase().includes(query)));
  if (state.sort === 'title') result.sort((a,b) => a.title.localeCompare(b.title));
  if (['oldest','newest'].includes(state.sort)) result.sort((a,b) => { const ay = a.years.length ? Math.min(...a.years) : null; const by = b.years.length ? Math.min(...b.years) : null; return ay === null ? (by === null ? 0 : 1) : by === null ? -1 : state.sort === 'oldest' ? ay-by : by-ay; });
  return result;
}
export function counts(records) {
  const decades = new Map();
  for (const r of records) for (const d of new Set(r.years.map(y => Math.floor(y/10)*10))) decades.set(d,(decades.get(d)||0)+1);
  return {records:records.length,institutions:new Set(records.flatMap(r => r.institutions)).size,undated:records.filter(r => !r.years.length).length,decades:[...decades].sort((a,b) => a[0]-b[0])};
}
export function citation(r, capture = '') {
  return [r.title,r.creators.length ? `Creator: ${r.creators.join('; ')}` : 'Creator: not supplied',`Institution: ${r.institutions.join('; ') || 'Not supplied'}`,`Recorded date: ${r.dateText.join('; ') || r.years.join(', ') || 'Not supplied'}`,`Image rights: ${r.rights.map(x => `${x.label} (${x.url})`).join('; ')}`,`Source: ${r.source || r.europeana}`,r.source && r.europeana ? `Europeana: ${r.europeana}` : '',`Captured: ${r.capturedAt || capture || 'Unknown'}`,'Place relationship: keyword match; not a verified depicted location.'].filter(Boolean).join('\n');
}
