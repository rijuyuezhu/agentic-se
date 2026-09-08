const segmenter = new Intl.Segmenter('zh-CN', { granularity: 'word' })

export function tokenize(text) {
  return Array.from(segmenter.segment(text), ({ segment, isWordLike }) =>
    isWordLike ? segment : ''
  ).filter(Boolean)
}

export const searchOptions = {
  fuzzy: 0.2,
  prefix: true,
  boost: { title: 4, text: 2, titles: 1 },
}

const TYPE_LABELS = {
  module: 'Module',
  lab: 'Lab',
  case_study: 'Case Study',
  source_audit: 'Source Audit',
  extension: 'Extension',
  practicum: 'Practicum',
  reference: 'Reference',
}

export function searchLabel(page, byId) {
  const type = TYPE_LABELS[page.type] ?? page.type
  if (page.type === 'module') return `${type} · ${page.id}`

  const relationIds = [...new Set([...(page.related ?? []), ...(page.related_by ?? [])])]
  const modules = relationIds
    .map((id) => byId.get(id))
    .filter((item) => item?.type === 'module')
    .sort((a, b) => (a.order ?? 999) - (b.order ?? 999) || a.id.localeCompare(b.id))
  return modules.length ? `${type} · ${modules.map((module) => module.id).join(' / ')}` : type
}
