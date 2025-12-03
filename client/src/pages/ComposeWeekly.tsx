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
    const [isGeneratingTemplate, setIsGeneratingTemplate] = useState(false);
    const [processingProgress, setProcessingProgress] = useState(0);
    const [dateInterval, setDateInterval] = useState<{ start: string; end: string } | null>(null);

    const hasRows = rows.length > 0;
    const hasCheckedItems = rows.some((row) => row.keep);

    const handleFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }
        setError(null);
        setIsLoading(true);
        setProcessingProgress(0);
        setDateInterval(null);
        setFileName(file.name.replace(/\.[^/.]+$/, ''));

        try {
            setProcessingProgress(20);
            const parsedRows = await parseWorkbook(file);
            if (!parsedRows.length) {
                setRows([]);
                setError('No rows found in the uploaded file. Ensure it contains headers like date, url, class_daily, title, abstract.');
                return;
            }
            setProcessingProgress(40);
            setRows(parsedRows);

            // Calculate date interval
            const dates = parsedRows.map(r => r.date).filter(Boolean).sort();
            if (dates.length > 0 && dates[0] && dates[dates.length - 1]) {
                setDateInterval({ start: dates[0], end: dates[dates.length - 1] });
            }

            setProcessingProgress(50);
            await fetchGeminiInsights(parsedRows);
            setProcessingProgress(100);
        } catch (err) {
            console.error(err);
            setError('Unable to read the uploaded file. Please verify the format and try again.');
        } finally {
            setIsLoading(false);
            setTimeout(() => setProcessingProgress(0), 1000);
        }
    };

    const handleEmailUpload = async (event: ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files;
        if (!files || files.length === 0) {
            return;
        }
        setError(null);
        setIsLoading(true);
        setProcessingProgress(0);
        setDateInterval(null);
        setFileName(`${files.length} email file(s)`);

        try {
            setProcessingProgress(20);
            // Parse email files via backend
            const newsItems = await ApiHelper.parseEmailFiles(files);

            if (!newsItems.length) {
                setRows([]);
                setError('No news items found in the uploaded email files.');
                return;
            }

            // Debug: Check what we received
            console.log('Received news items:', newsItems.slice(0, 2));

            setProcessingProgress(40);
            // Convert to ComposeWeeklyRow format
            const parsedRows: ComposeWeeklyRow[] = newsItems.map((item) => ({
                id: item.id,
                title: item.title,
                abstract: item.abstract || '',
                url: item.url || '',
                date: item.date || '',
                class_daily: item.class_daily || '',
                gemini_comment: '',
                gemini_classification: '',
                ci_comment: '',
                keep: true,
            }));

            setRows(parsedRows);

            // Calculate date interval
            const dates = parsedRows.map(r => r.date).filter(Boolean).sort();
            if (dates.length > 0 && dates[0] && dates[dates.length - 1]) {
                setDateInterval({ start: dates[0], end: dates[dates.length - 1] });
            }

            setProcessingProgress(50);
            await fetchGeminiInsights(parsedRows);
            setProcessingProgress(100);
        } catch (err) {
            console.error(err);
            setError('Unable to parse the email files. Please verify the format and try again.');
        } finally {
            setIsLoading(false);
            setTimeout(() => setProcessingProgress(0), 1000);
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
            setProcessingProgress(60);
            const requestItems: ComposeWeeklyItem[] = parsedRows.map((row) => ({
                id: row.id,
                title: row.title,
                abstract: row.abstract,
                url: row.url,
                date: row.date,
                class_daily: row.class_daily,
            }));
            setProcessingProgress(70);
            const insights: ComposeWeeklyInsight[] = await ApiHelper.analyzeComposeWeekly(requestItems);
            setProcessingProgress(90);
            setRows((currentRows) =>
                currentRows.map((row) => {
                    const match = insights.find((item) => item.id === row.id);
                    if (!match) {
                        return row;
                    }
                    return {
                        ...row,
                        // Use refined_title if available, otherwise keep original title
                        title: match.refined_title || row.title,
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

    const handleClassificationChange = (rowId: string, value: string) => {
        setRows((current) =>
            current.map((row) => (row.id === rowId ? { ...row, gemini_classification: value } : row)),
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

    const handleExportWeeklyTemplate = async () => {
        const checkedRows = rows.filter((row) => row.keep);
        if (checkedRows.length === 0) {
            alert('Please select at least one news item to include in the template.');
            return;
        }

        setIsGeneratingTemplate(true);
        setError(null);

        try {
            // Prepare news items for the API
            const newsItems = checkedRows.map((row) => ({
                title: row.title,
                abstract: row.abstract,
                url: row.url,
                gemini_classification: row.gemini_classification,
                ci_comment: row.ci_comment || row.gemini_comment,
                gemini_comment: row.gemini_comment,
            }));

            // Generate the template
            const html = await ApiHelper.generateWeeklyTemplate(newsItems);

            // Download the generated HTML
            const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `weekly-newsletter-${new Date().toISOString().split('T')[0]}.html`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Error generating weekly template:', err);
            setError('Failed to generate weekly template. Please try again.');
        } finally {
            setIsGeneratingTemplate(false);
        }
    };

    const allowedClasses = useMemo(() => ComposeWeeklyClasses.join(', '), []);

    return (
        <div className="flex-1 overflow-auto bg-gray-50 dark:bg-slate-900 text-gray-900 dark:text-slate-100">
            <div className="max-w-[90%] mx-auto p-6 space-y-6">
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
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                                Upload an Excel file with columns: date, url, title, abstract, class_daily.
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2" htmlFor="email-upload">
                                Upload Email files (.eml)
                            </label>
                            <input
                                id="email-upload"
                                type="file"
                                accept=".eml"
                                multiple
                                onChange={handleEmailUpload}
                                className="block w-full text-sm text-gray-600 dark:text-slate-200 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100 dark:file:bg-green-900 dark:file:text-green-100"
                            />
                            <p className="mt-2 text-xs text-gray-500 dark:text-slate-400">
                                Upload Industry News Review email files. Multiple files can be selected.
                            </p>
                        </div>
                    </div>

                    <p className="text-xs text-gray-500 dark:text-slate-400">
                        Gemini classification options: {allowedClasses}.
                    </p>

                    {isLoading && (
                        <div className="space-y-4 bg-blue-50 dark:bg-blue-900/20 p-6 rounded-lg border-2 border-blue-400 dark:border-blue-600">
                            <div className="flex justify-between items-center mb-2">
                                <p className="text-sm font-semibold text-blue-900 dark:text-blue-100">
                                    Processing file...
                                </p>
                                <p className="text-xs text-blue-700 dark:text-blue-300 font-medium">
                                    {processingProgress}%
                                </p>
                            </div>

                            {dateInterval && (
                                <div className="flex items-center justify-center gap-3 text-sm text-blue-800 dark:text-blue-200 font-medium mb-3">
                                    <span className="bg-blue-200 dark:bg-blue-800 px-3 py-1 rounded-md">{dateInterval.start}</span>
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                                    </svg>
                                    <span className="bg-blue-200 dark:bg-blue-800 px-3 py-1 rounded-md">{dateInterval.end}</span>
                                </div>
                            )}

                            <div className="w-full bg-blue-200 dark:bg-blue-900 rounded-full h-8 overflow-hidden shadow-inner">
                                <div
                                    className="bg-gradient-to-r from-blue-500 via-blue-600 to-blue-700 h-full rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-3"
                                    style={{ width: `${processingProgress}%` }}
                                >
                                    {processingProgress > 10 && (
                                        <span className="text-white text-xs font-bold drop-shadow-lg">
                                            {processingProgress}%
                                        </span>
                                    )}
                                </div>
                            </div>

                            <p className="text-xs text-blue-700 dark:text-blue-300 text-center">
                                {processingProgress < 40 && 'Reading file...'}
                                {processingProgress >= 40 && processingProgress < 50 && 'Parsing content...'}
                                {processingProgress >= 50 && processingProgress < 100 && 'Analyzing with Gemini AI...'}
                                {processingProgress >= 100 && 'Complete!'}
                            </p>
                        </div>
                    )}

                    {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
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
                                <button
                                    type="button"
                                    onClick={handleExportWeeklyTemplate}
                                    className="px-4 py-2 rounded-md bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                    disabled={!hasCheckedItems || isGeneratingTemplate}
                                >
                                    {isGeneratingTemplate ? 'Generating...' : 'Export Weekly Template'}
                                </button>
                            </div>
                        </div>
                        <div className="overflow-visible">
                            <table className="w-full divide-y divide-gray-200 dark:divide-slate-700 text-sm table-fixed">
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
                                            <td className="px-4 py-3 align-top group relative">
                                                <div className="line-clamp-2 text-sm text-gray-700 dark:text-slate-200 cursor-pointer">
                                                    {row.abstract || '—'}
                                                </div>
                                                {row.abstract && (
                                                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 absolute left-0 top-0 z-50 w-96 p-4 bg-white dark:bg-slate-800 border-2 border-blue-500 rounded-lg shadow-2xl">
                                                        <div className="text-sm text-gray-700 dark:text-slate-200 whitespace-normal">
                                                            {row.abstract}
                                                        </div>
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-4 py-3 align-top w-44">
                                                <select
                                                    value={row.gemini_classification || ''}
                                                    onChange={(e) => handleClassificationChange(row.id, e.target.value)}
                                                    className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-xs font-medium text-blue-700 dark:text-blue-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                                >
                                                    <option value="">Select classification...</option>
                                                    {ComposeWeeklyClasses.map((cls) => (
                                                        <option key={cls} value={cls}>
                                                            {cls}
                                                        </option>
                                                    ))}
                                                </select>
                                            </td>
                                            <td className="px-4 py-3 align-top group relative">
                                                <div className="line-clamp-2 text-sm text-gray-700 dark:text-slate-200 cursor-pointer">
                                                    {row.gemini_comment || '—'}
                                                </div>
                                                {row.gemini_comment && (
                                                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 absolute left-0 top-0 z-50 w-96 p-4 bg-white dark:bg-slate-800 border-2 border-blue-500 rounded-lg shadow-2xl">
                                                        <div className="text-sm text-gray-700 dark:text-slate-200 whitespace-normal">
                                                            {row.gemini_comment}
                                                        </div>
                                                    </div>
                                                )}
                                            </td>
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
                                            <td className="px-4 py-3 align-top group relative">
                                                <div className="line-clamp-2 text-sm text-gray-700 dark:text-slate-200 cursor-pointer">
                                                    {finalComment(row) || '—'}
                                                </div>
                                                {finalComment(row) && (
                                                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 absolute left-0 top-0 z-50 w-96 p-4 bg-white dark:bg-slate-800 border-2 border-blue-500 rounded-lg shadow-2xl">
                                                        <div className="text-sm text-gray-700 dark:text-slate-200 whitespace-normal">
                                                            {finalComment(row)}
                                                        </div>
                                                    </div>
                                                )}
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
