import React, { useMemo, useState } from "react";
import { Download, Search } from "lucide-react";

const PAGE_SIZE = 20;

export function downloadCSV(filename, rows, columns) {
  const escape = (v) => {
    if (v === null || v === undefined) return "";
    const s = typeof v === "object" ? JSON.stringify(v) : String(v);
    return s.includes(",") || s.includes('"') || s.includes("\n") ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = columns.map(c => c.label).join(",");
  const body = rows.map(r => columns.map(c => escape(typeof c.csv === "function" ? c.csv(r) : r[c.key])).join(",")).join("\n");
  const blob = new Blob([header + "\n" + body], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

/**
 * Generic admin table with client-side search, filter, pagination, CSV export and row-click.
 *
 * columns: [{ key, label, render?, csv?, sortable? }]
 * filters: [{ key, label, options: [{value, label}] }]
 * searchKeys: string[] of row keys to search across
 */
export default function AdminTable({ data, columns, filters = [], searchKeys = [], onRowClick, exportName = "export", testid }) {
  const [q, setQ] = useState("");
  const [activeFilters, setActiveFilters] = useState({});
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    const ql = q.toLowerCase().trim();
    return (data || []).filter(row => {
      // search
      if (ql) {
        const hay = searchKeys.map(k => String(row[k] ?? "").toLowerCase()).join(" ");
        if (!hay.includes(ql)) return false;
      }
      // filters
      for (const [k, v] of Object.entries(activeFilters)) {
        if (!v) continue;
        if (String(row[k] ?? "") !== String(v)) return false;
      }
      return true;
    });
  }, [data, q, activeFilters, searchKeys]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const rows = filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  return (
    <div data-testid={testid}>
      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-center mb-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"/>
          <input
            data-testid={`${testid}-search`}
            value={q} onChange={(e) => { setQ(e.target.value); setPage(0); }}
            placeholder="Search…"
            className="brutal-input !pl-9"
          />
        </div>
        {filters.map(f => (
          <select
            key={f.key}
            data-testid={`${testid}-filter-${f.key}`}
            value={activeFilters[f.key] || ""}
            onChange={(e) => { setActiveFilters({ ...activeFilters, [f.key]: e.target.value }); setPage(0); }}
            className="brutal-input !w-auto"
          >
            <option value="">All {f.label}</option>
            {f.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        ))}
        <button
          onClick={() => downloadCSV(`${exportName}-${Date.now()}.csv`, filtered, columns)}
          data-testid={`${testid}-export`}
          className="brutal-btn !py-2 !px-3 flex items-center gap-2 text-xs"
        ><Download size={12}/>CSV ({filtered.length})</button>
      </div>

      {/* Table */}
      <div className="brutal-card p-0 overflow-x-auto">
        <table className="w-full" data-testid={`${testid}-table`}>
          <thead><tr className="border-b border-[#222]">
            {columns.map(c => <th key={c.key} className="overline text-left py-3 px-4">{c.label}</th>)}
          </tr></thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan={columns.length} className="py-8 px-4 font-mono text-zinc-500 text-center">No matching rows.</td></tr>
            ) : rows.map((r, i) => (
              <tr
                key={r.id || i}
                onClick={() => onRowClick && onRowClick(r)}
                data-testid={`${testid}-row-${r.id || i}`}
                className={`border-b border-[#222] ${onRowClick ? "hover:bg-[#0a0a0a] cursor-pointer" : ""}`}>
                {columns.map(c => (
                  <td key={c.key} className="py-3 px-4 font-mono text-xs align-top">
                    {c.render ? c.render(r) : (r[c.key] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pageCount > 1 && (
        <div className="flex justify-between items-center mt-3 font-mono text-xs text-zinc-500">
          <div>Page {safePage + 1} of {pageCount} · {filtered.length} rows</div>
          <div className="flex gap-2">
            <button onClick={() => setPage(0)} disabled={safePage === 0} data-testid={`${testid}-first`} className="brutal-btn !py-1 !px-3 text-xs">««</button>
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={safePage === 0} data-testid={`${testid}-prev`} className="brutal-btn !py-1 !px-3 text-xs">‹ Prev</button>
            <button onClick={() => setPage(p => Math.min(pageCount - 1, p + 1))} disabled={safePage >= pageCount - 1} data-testid={`${testid}-next`} className="brutal-btn !py-1 !px-3 text-xs">Next ›</button>
            <button onClick={() => setPage(pageCount - 1)} disabled={safePage >= pageCount - 1} data-testid={`${testid}-last`} className="brutal-btn !py-1 !px-3 text-xs">»»</button>
          </div>
        </div>
      )}
    </div>
  );
}
