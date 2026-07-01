'use client'

import React from 'react'
import { T } from '@/lib/stockData'

interface MarkdownRendererProps {
  content: string
}

function parseInline(text: string): React.ReactNode[] {
  let parts: React.ReactNode[] = [text]

  // Inline Code: `code`
  parts = parts.flatMap((part, pIdx) => {
    if (typeof part !== 'string') return part
    const segments = part.split(/`([^`]+)`/g)
    return segments.map((seg, idx) => {
      if (idx % 2 === 1) {
        return (
          <code
            key={`inline-code-${pIdx}-${idx}`}
            className="px-1 py-0.5 rounded text-xs border bg-elevated text-textPrimary"
            style={{
              fontFamily: T.mono,
              background: T.el,
              border: `1px solid ${T.b}`,
              padding: '2px 4px',
              borderRadius: 4,
              fontSize: '11px',
            }}
          >
            {seg}
          </code>
        )
      }
      return seg
    })
  })

  // Bold: **text**
  parts = parts.flatMap((part, pIdx) => {
    if (typeof part !== 'string') return part
    const segments = part.split(/\*\*([^*]+)\*\*/g)
    return segments.map((seg, idx) => {
      if (idx % 2 === 1) {
        return <strong key={`bold-${pIdx}-${idx}`} className="font-bold text-textPrimary" style={{ color: T.text, fontWeight: 700 }}>{seg}</strong>
      }
      return seg
    })
  })

  // Italic: *text*
  parts = parts.flatMap((part, pIdx) => {
    if (typeof part !== 'string') return part
    const segments = part.split(/\*([^*]+)\*/g)
    return segments.map((seg, idx) => {
      if (idx % 2 === 1) {
        return <em key={`italic-${pIdx}-${idx}`} className="italic">{seg}</em>
      }
      return seg
    })
  })

  // Links: [label](url)
  parts = parts.flatMap((part, pIdx) => {
    if (typeof part !== 'string') return part
    const segments = part.split(/\[([^\]]+)\]\(([^)]+)\)/g)
    const result: React.ReactNode[] = []
    let i = 0
    while (i < segments.length) {
      result.push(segments[i])
      if (i + 1 < segments.length) {
        const label = segments[i + 1]
        const url = segments[i + 2]
        result.push(
          <a
            key={`link-${pIdx}-${i}`}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand hover:underline font-medium"
            style={{ color: T.blue, textDecoration: 'underline' }}
          >
            {label}
          </a>
        )
        i += 3
      } else {
        i += 1
      }
    }
    return result
  })

  return parts
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  if (!content) return null

  const parts = content.split('```')
  const blocks: React.ReactNode[] = []

  parts.forEach((part, index) => {
    if (index % 2 === 1) {
      // Code block
      const lineBreakIndex = part.indexOf('\n')
      let lang = ''
      let code = part
      if (lineBreakIndex !== -1) {
        const possibleLang = part.substring(0, lineBreakIndex).trim()
        if (possibleLang.length > 0 && possibleLang.length < 15 && /^[a-zA-Z0-9+#_]+$/.test(possibleLang)) {
          lang = possibleLang
          code = part.substring(lineBreakIndex + 1)
        }
      }

      if (code.endsWith('\n')) {
        code = code.slice(0, -1)
      }

      blocks.push(
        <div key={`code-block-${index}`} className="my-3 rounded-lg overflow-hidden border bg-elevated/40" style={{ border: `1px solid ${T.b}`, background: `color-mix(in srgb, ${T.el} 40%, transparent)` }}>
          {lang && (
            <div className="px-4 py-1.5 border-b text-[10px] font-mono font-bold tracking-wider uppercase flex justify-between items-center" style={{ borderBottom: `1px solid ${T.b}`, color: T.muted, background: T.el }}>
              <span>{lang}</span>
            </div>
          )}
          <pre className="p-4 overflow-x-auto text-xs leading-relaxed font-mono select-all" style={{ fontFamily: T.mono, color: T.text, margin: 0 }}>
            <code>{code}</code>
          </pre>
        </div>
      )
    } else {
      // Regular text block
      const lines = part.split('\n')
      let i = 0
      while (i < lines.length) {
        const line = lines[i]
        const trimmed = line.trim()

        if (trimmed === '') {
          i++
          continue
        }

        // 1. Headings
        if (trimmed.startsWith('#')) {
          const match = trimmed.match(/^(#{1,6})\s+(.*)$/)
          if (match) {
            const level = match[1].length
            const text = match[2]
            const sizeStyle = level === 1 ? { fontSize: '1.4rem', marginTop: '1.25rem', marginBottom: '0.5rem' } :
                              level === 2 ? { fontSize: '1.2rem', marginTop: '1rem', marginBottom: '0.4rem' } :
                              { fontSize: '1.05rem', marginTop: '0.75rem', marginBottom: '0.3rem' }

            blocks.push(
              <div key={`heading-${index}-${i}`} style={{ fontWeight: 700, color: T.text, ...sizeStyle }}>
                {parseInline(text)}
              </div>
            )
            i++
            continue
          }
        }

        // 2. Blockquotes
        if (trimmed.startsWith('>')) {
          let quoteContent = trimmed.substring(1).trim()
          let j = i + 1
          while (j < lines.length && lines[j].trim().startsWith('>')) {
            quoteContent += '\n' + lines[j].trim().substring(1).trim()
            j++
          }
          blocks.push(
            <blockquote key={`blockquote-${index}-${i}`} className="pl-4 border-l-4 my-2 italic" style={{ borderLeft: `3px solid ${T.blue}`, paddingLeft: 12, margin: '8px 0', color: T.sub }}>
              {quoteContent.split('\n').map((qLine, lIdx) => (
                <p key={`bq-p-${lIdx}`} style={{ margin: '4px 0' }}>{parseInline(qLine)}</p>
              ))}
            </blockquote>
          )
          i = j
          continue
        }

        // 3. Tables
        if (trimmed.startsWith('|')) {
          const tableLines: string[] = []
          let j = i
          while (j < lines.length && lines[j].trim().startsWith('|')) {
            tableLines.push(lines[j].trim())
            j++
          }

          if (tableLines.length >= 2) {
            const isDivider = tableLines[1].replace(/[\s\-|:|]/g, '') === ''
            if (isDivider) {
              const parseRow = (rowText: string) => {
                const cols = rowText.split('|')
                if (cols[0] === '') cols.shift()
                if (cols[cols.length - 1] === '') cols.pop()
                return cols.map(c => c.trim())
              }

              const headers = parseRow(tableLines[0])
              const rows = tableLines.slice(2).map(parseRow)

              blocks.push(
                <div key={`table-${index}-${i}`} className="overflow-x-auto my-3 border rounded-lg" style={{ border: `1px solid ${T.b}`, borderRadius: 8 }}>
                  <table className="w-full text-left border-collapse text-xs" style={{ width: '100%' }}>
                    <thead>
                      <tr className="border-b" style={{ borderBottom: `1px solid ${T.b}`, background: `color-mix(in srgb, ${T.el} 40%, transparent)` }}>
                        {headers.map((h, hIdx) => (
                          <th key={`th-${hIdx}`} className="p-2.5 font-semibold" style={{ color: T.muted, padding: '10px' }}>
                            {parseInline(h)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody style={{ color: T.text }}>
                      {rows.map((row, rIdx) => (
                        <tr key={`tr-${rIdx}`} style={{ borderBottom: rIdx < rows.length - 1 ? `1px solid ${T.b}` : 'none' }}>
                          {headers.map((_, cIdx) => (
                            <td key={`td-${rIdx}-${cIdx}`} className="p-2.5 font-mono" style={{ padding: '10px', fontSize: '11px' }}>
                              {parseInline(row[cIdx] || '')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
              i = j
              continue
            }
          }
        }

        // 4. Unordered Lists
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('+ ')) {
          const listItems: string[] = []
          let j = i
          while (j < lines.length) {
            const nextTrim = lines[j].trim()
            if (nextTrim.startsWith('- ') || nextTrim.startsWith('* ') || nextTrim.startsWith('+ ')) {
              listItems.push(nextTrim.substring(2))
              j++
            } else if (nextTrim === '') {
              if (j + 1 < lines.length && (lines[j+1].trim().startsWith('- ') || lines[j+1].trim().startsWith('* ') || lines[j+1].trim().startsWith('+ '))) {
                j++
              } else {
                break
              }
            } else {
              break
            }
          }

          blocks.push(
            <ul key={`ul-${index}-${i}`} className="list-disc pl-5 my-2 space-y-1" style={{ paddingLeft: 20, margin: '8px 0', listStyleType: 'disc', color: T.sub }}>
              {listItems.map((item, itemIdx) => (
                <li key={`ul-li-${itemIdx}`} style={{ margin: '4px 0' }}>{parseInline(item)}</li>
              ))}
            </ul>
          )
          i = j
          continue
        }

        // 5. Ordered Lists
        if (/^\d+\.\s+/.test(trimmed)) {
          const listItems: string[] = []
          let j = i
          while (j < lines.length) {
            const nextTrim = lines[j].trim()
            const listMatch = nextTrim.match(/^(\d+)\.\s+(.*)$/)
            if (listMatch) {
              listItems.push(listMatch[2])
              j++
            } else if (nextTrim === '') {
              if (j + 1 < lines.length && /^\d+\.\s+/.test(lines[j+1].trim())) {
                j++
              } else {
                break
              }
            } else {
              break
            }
          }

          blocks.push(
            <ol key={`ol-${index}-${i}`} className="list-decimal pl-5 my-2 space-y-1" style={{ paddingLeft: 20, margin: '8px 0', listStyleType: 'decimal', color: T.sub }}>
              {listItems.map((item, itemIdx) => (
                <li key={`ol-li-${itemIdx}`} style={{ margin: '4px 0' }}>{parseInline(item)}</li>
              ))}
            </ol>
          )
          i = j
          continue
        }

        // 6. Normal Paragraph
        let paragraphText = trimmed
        let j = i + 1
        while (j < lines.length) {
          const nextLine = lines[j]
          const nextTrim = nextLine.trim()
          if (nextTrim === '' ||
              nextTrim.startsWith('#') ||
              nextTrim.startsWith('|') ||
              nextTrim.startsWith('- ') ||
              nextTrim.startsWith('* ') ||
              nextTrim.startsWith('+ ') ||
              /^\d+\.\s+/.test(nextTrim) ||
              nextTrim.startsWith('>')) {
            break
          }
          paragraphText += ' ' + nextTrim
          j++
        }

        blocks.push(
          <p key={`p-${index}-${i}`} style={{ margin: '8px 0', color: T.text, lineHeight: 1.6 }}>
            {parseInline(paragraphText)}
          </p>
        )
        i = j
      }
    }
  })

  return <div className="leading-relaxed text-sm" style={{ color: T.text }}>{blocks}</div>
}
