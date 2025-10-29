import React, { ChangeEvent, useMemo, useState } from 'react';
import * as XLSX from 'xlsx';
import ApiHelper from '../backend/ApiHelper';
import { ComposeWeeklyClasses, ComposeWeeklyItem, ComposeWeeklyInsight } from '../dto/InterfaceDefinition';

interface ComposeWeeklyRow extends ComposeWeeklyItem {
    gemini_comment: string;
    gemini_classification: string;
    similarity?: number;
    ci_comment: string;
    keep: boolean;
}

const ComposeWeekly: React.FC = () => {
    const [rows, setRows] = useState<ComposeWeeklyRow[]>([]);
    const [fileName, setFileName] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const hasRows = rows.length > 0;

    const handleFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }
        setError(null);
        setIsLoading(true);
        setFileName(file.name.replace(/\.[^/.]+$/, ''));

        try {
            const parsedRows = await parseWorkbook(file);
            if (!parsedRows.length) {
                setRows([]);
                setError('No rows found in the uploaded file. Ensure it contains headers like date, url, class_daily, title, abstract.');
                return;
            }
            setRows(parsedRows);
            await fetchGeminiInsights(parsedRows);
        } catch (err) {
            console.error(err);
            setError('Unable to read the uploaded file. Please verify the format and try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const parseWorkbook = async (file: File): Promise<ComposeWeeklyRow[]> => {
        const arrayBuffer = await file.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { type: 'array' });
        const firstSheet = workbook.SheetNames[0];
        if (!firstSheet) {
            return [];
        }
        const worksheet = workbook.Sheets[firstSheet];
        const sheetRows: Record<string, string>[] = XLSX.utils.sheet_to_json<Record<string, string>>(worksheet, {
            defval: '',
            raw: false,
        });

        const normalise = (value: unknown) => (typeof value === 'string' ? value.trim() : value ?? '').toString();

        const keyVariants = (base: string) => [base, base.toLowerCase(), base.toUpperCase(), base.replace(/[-\s]+/g, '_'), base.replace(/[-\s]+/g, '').toLowerCase()];

        const pickValue = (row: Record<string, string>, keys: string[]) => {
            for (const key of keys) {
                const candidates = keyVariants(key);
                for (const candidate of candidates) {
                    if (candidate in row) {
                        return normalise(row[candidate]);
                    }
                }
            }
            return '';
        };

        return sheetRows
            .map((row, index) => {
                const title = pickValue(row, ['title']);
                const abstract = pickValue(row, ['abstract', 'summary']);
                const url = pickValue(row, ['url', 'link']);
                const date = pickValue(row, ['date']);
                const classDaily = pickValue(row, ['class_daily', 'class daily', 'category']);

                if (!title && !abstract) {
                    return null;
                }

                return {
                    id: pickValue(row, ['id', 'row_id']) || `${index}`,
                    title,
                    abstract,
                    url,
                    date,
                    class_daily: classDaily,
                    gemini_comment: '',
                    gemini_classification: '',
                    ci_comment: '',
                    keep: true, // By default, keep all items
                } as ComposeWeeklyRow;
            })
            .filter((entry): entry is ComposeWeeklyRow => Boolean(entry));
    };

    const fetchGeminiInsights = async (parsedRows: ComposeWeeklyRow[]) => {
        try {
            const requestItems: ComposeWeeklyItem[] = parsedRows.map((row) => ({
                id: row.id,
                title: row.title,
                abstract: row.abstract,
                url: row.url,
                date: row.date,
                class_daily: row.class_daily,
            }));
            const insights: ComposeWeeklyInsight[] = await ApiHelper.analyzeComposeWeekly(requestItems);
            setRows((currentRows) =>
                currentRows.map((row) => {
                    const match = insights.find((item) => item.id === row.id);
                    if (!match) {
                        return row;
                    }
                    return {
                        ...row,
                        gemini_comment: match.gemini_comment,
                        gemini_classification: match.gemini_classification,
                        similarity: (match as any).similarity,
                    };
                }),
            );
        } catch (err: unknown) {
            // Log full error for debugging
            console.error('Gemini insights failed', err);

            // Prefer server-provided error payload when available
            let message = 'Failed to retrieve Gemini insights. You can still add CI comments manually.';
            try {
                const errAny = err as any;
                if (errAny && errAny.response && errAny.response.data) {
                    // If server returned an error object, show a concise representation
                    const data = errAny.response.data;
                    if (typeof data === 'string') {
                        message = `Failed to retrieve Gemini insights: ${data}. You can still add CI comments manually.`;
                    } else if (data && data.error) {
                        message = `Failed to retrieve Gemini insights: ${String(data.error)}. You can still add CI comments manually.`;
                    } else {
                        message = `Failed to retrieve Gemini insights (status ${errAny.response.status}). You can still add CI comments manually.`;
                    }
                } else if (errAny && errAny.message) {
                    message = `Failed to retrieve Gemini insights: ${errAny.message}. You can still add CI comments manually.`;
                }
            } catch {
                // ignore formatting errors
            }
            setError(message);
        }
    };

    type SortKey = 'none' | 'similarity';
    type SortDir = 'asc' | 'desc';
    const [sortKey, setSortKey] = useState<SortKey>('none');
    const [sortDir, setSortDir] = useState<SortDir>('desc');
    const [minSimilarity, setMinSimilarity] = useState<number>(0);

    const toggleSort = (key: SortKey) => {
        if (sortKey !== key) {
            setSortKey(key);
            setSortDir('desc');
        } else {
            setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
        }
    };

    const displayedRows = useMemo(() => {
        // Apply filters first
        let arr = rows.filter((r) => {
            if (minSimilarity > 0) {
                const s = r.similarity;
                if (s == null || s < minSimilarity) return false;
            }
            return true;
        });
        // Then sort
        if (sortKey !== 'none') {
            arr = [...arr].sort((a, b) => {
                const av = (a as any)[sortKey] ?? -Infinity;
                const bv = (b as any)[sortKey] ?? -Infinity;
                if (av === bv) return 0;
                return sortDir === 'desc' ? (bv as number) - (av as number) : (av as number) - (bv as number);
            });
        }
        return arr;
    }, [rows, sortKey, sortDir, minSimilarity]);

    const handleCiCommentChange = (rowId: string, value: string) => {
        setRows((current) =>
            current.map((row) => (row.id === rowId ? { ...row, ci_comment: value } : row)),
        );
    };

    const handleKeepChange = (rowId: string, checked: boolean) => {
        setRows((current) =>
            current.map((row) => (row.id === rowId ? { ...row, keep: checked } : row)),
        );
    };

    const finalComment = (row: ComposeWeeklyRow) => {
        return row.ci_comment?.trim() ? row.ci_comment : row.gemini_comment;
    };

    // Helper function to get heatmap color based on similarity score (0-100)
    const getSimilarityColor = (similarity: number | undefined): string => {
        if (similarity == null) return 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400';

        // Heatmap gradient: red (low) -> yellow (mid) -> green (high)
        if (similarity >= 80) {
            return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 font-semibold';
        } else if (similarity >= 70) {
            return 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400';
        } else if (similarity >= 60) {
            return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300';
        } else if (similarity >= 50) {
            return 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300';
        } else {
            return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300';
        }
    };

    const handleExportExcel = () => {
        if (!hasRows) {
            return;
        }
        const exportRows = rows
            .filter((row) => row.keep) // Only export items marked to keep
            .map((row) => ({
                date: row.date,
                url: row.url,
                class_daily: row.class_daily,
                title: row.title,
                abstract: row.abstract,
                gemini_classification: row.gemini_classification,
                gemini_comment: row.gemini_comment,
                similarity: row.similarity ?? '',
                ci_comment: row.ci_comment,
                final_comment: finalComment(row),
            }));

        const worksheet = XLSX.utils.json_to_sheet(exportRows);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, 'ComposeWeekly');

        const exportFileName = `${fileName ?? 'compose-weekly'}-report.xlsx`;
        XLSX.writeFile(workbook, exportFileName);
    };

    const handleExportHtml = () => {
        if (!hasRows) {
            return;
        }

        const tableRows = rows
            .filter((row) => row.keep) // Only export items marked to keep
            .map(
                (row) => `
            <tr>
                <td>${escapeHtml(row.date)}</td>
                <td>${escapeHtml(row.title)}</td>
                <td>${escapeHtml(row.url)}</td>
                <td>${escapeHtml(row.class_daily)}</td>
                <td>${escapeHtml(row.abstract)}</td>
                <td>${escapeHtml(row.gemini_classification)}</td>
                <td>${escapeHtml(row.gemini_comment)}</td>
                <td>${escapeHtml(String(row.similarity ?? ''))}</td>
                <td>${escapeHtml(row.ci_comment)}</td>
                <td>${escapeHtml(finalComment(row))}</td>
            </tr>
        `,
            )
            .join('');

        const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Compose Weekly Report</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 24px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #bbbbbb; padding: 8px; text-align: left; vertical-align: top; }
        th { background-color: #f4f4f4; }
    </style>
</head>
<body>
    <h1>Compose Weekly Report</h1>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Title</th>
                <th>URL</th>
                <th>Class Daily</th>
                <th>Abstract</th>
                <th>Gemini Classification</th>
                <th>Gemini Comment</th>
                <th>Similarity</th>
                <th>CI Comment</th>
                <th>Final Comment</th>
            </tr>
        </thead>
        <tbody>
            ${tableRows}
        </tbody>
    </table>
</body>
</html>`;

        const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${fileName ?? 'compose-weekly'}-report.html`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    const allowedClasses = useMemo(() => ComposeWeeklyClasses.join(', '), []);

    return (
        <div className="flex-1 overflow-auto bg-gray-50 dark:bg-slate-900 text-gray-900 dark:text-slate-100">
            <div className="max-w-6xl mx-auto p-6 space-y-6">
                <header className="space-y-2">
                    <h1 className="text-2xl font-semibold">Compose Your Weekly</h1>
                    <p className="text-sm text-gray-600 dark:text-slate-300">
                        Upload an Excel workbook with columns such as <code>date</code>, <code>url</code>,{' '}
                        <code>class_daily</code>, <code>title</code>, and <code>abstract</code>. Gemini will provide
                        an initial comment and classification. You can overwrite the comment by adding your own CI
                        insight—the exported report will always use the CI comment when present.
                    </p>
                </header>

                <section className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 space-y-4 shadow-sm">
                    <div>
                        <label className="block text-sm font-medium mb-2" htmlFor="compose-upload">
                            Upload Excel file
                        </label>
                        <input
                            id="compose-upload"
                            type="file"
                            accept=".xlsx,.xls,.xlsm"
                            onChange={handleFileUpload}
                            className="block w-full text-sm text-gray-600 dark:text-slate-200 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-slate-700 dark:file:text-slate-100"
                        />
                        <p className="mt-2 text-xs text-gray-500 dark:text-slate-400">
                            Gemini classification options: {allowedClasses}.
                        </p>
                    </div>
                    {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
                    {isLoading && <p className="text-sm text-blue-600 dark:text-blue-300">Processing file…</p>}
                </section>

                {hasRows && (
                    <section className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm">
                        <div className="flex flex-wrap items-center justify-between gap-4 p-4 border-b border-gray-200 dark:border-slate-700">
                            <div>
                                <h2 className="text-lg font-semibold">News Items</h2>
                                <p className="text-xs text-gray-500 dark:text-slate-400">
                                    Gemini comment and classification are locked. Add CI comments to tailor the newsletter—these will be used
                                    when exporting.
                                </p>
                            </div>
                            <div className="flex flex-wrap items-center gap-3">
                                <div className="flex items-center gap-2 text-sm">
                                    <label htmlFor="min-similarity" className="text-gray-600 dark:text-slate-300">Min Similarity:</label>
                                    <select
                                        id="min-similarity"
                                        value={minSimilarity}
                                        onChange={(e) => setMinSimilarity(parseInt(e.target.value, 10))}
                                        className="border border-gray-300 dark:border-slate-600 rounded px-2 py-1 bg-white dark:bg-slate-900"
                                    >
                                        <option value={0}>Any</option>
                                        <option value={60}>60+</option>
                                        <option value={70}>70+</option>
                                        <option value={80}>80+</option>
                                        <option value={90}>90+</option>
                                    </select>
                                </div>
                                <button
                                    type="button"
                                    onClick={handleExportExcel}
                                    className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                                    disabled={!hasRows}
                                >
                                    Export Excel
                                </button>
                                <button
                                    type="button"
                                    onClick={handleExportHtml}
                                    className="px-4 py-2 rounded-md bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
                                    disabled={!hasRows}
                                >
                                    Export HTML
                                </button>
                            </div>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-700 text-sm">
                                <thead className="bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-100">
                                    <tr>
                                        <th className="px-2 py-3 text-center font-medium align-middle">Keep?</th>
                                        <th className="px-4 py-3 text-center font-medium align-middle">Date</th>
                                        <th className="px-4 py-3 text-center font-medium align-middle">Title</th>
                                        <th className="px-4 py-3 text-center font-medium align-middle">Class Daily</th>
                                        <th className="px-4 py-3 text-center font-medium align-middle">Abstract</th>
                                        <th className="px-4 py-3 text-center font-medium align-middle">
                                            <span className="whitespace-pre-line">Gemini -{'\n'}Classification</span>
                                        </th>
                                        <th className="px-4 py-3 text-center font-medium align-middle">
                                            <span className="whitespace-pre-line">Gemini -{'\n'}Comment</span>
                                        </th>
                                        <th
                                            className="px-4 py-3 text-center font-medium align-middle cursor-pointer select-none"
                                            onClick={() => toggleSort('similarity')}
                                            title="Sort by Similarity"
                                        >
                                            <span className="whitespace-pre-line">Gemini -{'\n'}Similarity {sortKey === 'similarity' ? (sortDir === 'desc' ? '▼' : '▲') : ''}</span>
                                        </th>
                                        <th className="px-4 py-3 text-center font-medium align-middle">
                                            <span className="whitespace-pre-line">CI -{'\n'}Comment</span>
                                        </th>
                                        <th className="px-4 py-3 text-center font-medium align-middle">Final Comment</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white dark:bg-slate-800 divide-y divide-gray-200 dark:divide-slate-700">
                                    {displayedRows.map((row) => (
                                        <tr key={row.id}>
                                            <td className="px-2 py-3 align-top text-center w-16">
                                                <input
                                                    type="checkbox"
                                                    checked={row.keep}
                                                    onChange={(e) => handleKeepChange(row.id, e.target.checked)}
                                                    className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600 cursor-pointer"
                                                />
                                            </td>
                                            <td className="px-4 py-3 align-top w-28">{row.date}</td>
                                            <td className="px-4 py-3 align-top w-64">
                                                {row.url ? (
                                                    <a
                                                        href={row.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-blue-600 dark:text-blue-300 underline hover:text-blue-800 dark:hover:text-blue-400"
                                                    >
                                                        {row.title}
                                                    </a>
                                                ) : (
                                                    <span>{row.title}</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-3 align-top w-40">{row.class_daily || '—'}</td>
                                            <td className="px-4 py-3 align-top w-72">{row.abstract || '—'}</td>
                                            <td className="px-4 py-3 align-top w-44">
                                                <span className="inline-flex items-center rounded-full bg-blue-50 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200 px-3 py-1 text-xs font-medium">
                                                    {row.gemini_classification || 'Pending'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 align-top w-72">{row.gemini_comment || '—'}</td>
                                            <td className="px-2 py-3 align-top w-16 text-center">
                                                <span className={`inline-block px-2 py-1 rounded-md text-xs font-medium ${getSimilarityColor(row.similarity)}`}>
                                                    {row.similarity ?? '—'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 align-top w-72">
                                                <textarea
                                                    value={row.ci_comment}
                                                    onChange={(e) => handleCiCommentChange(row.id, e.target.value)}
                                                    placeholder="Add your CI insight…"
                                                    className="w-full resize-y rounded border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2 text-sm"
                                                    rows={4}
                                                />
                                            </td>
                                            <td className="px-4 py-3 align-top w-72 text-sm text-gray-700 dark:text-slate-200">
                                                {finalComment(row) || '—'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>
                )}
            </div>
        </div>
    );
};

const escapeHtml = (value: string | undefined) => {
    const safe = value ?? '';
    return safe
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
};

export default ComposeWeekly;
